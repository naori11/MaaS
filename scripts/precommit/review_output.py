"""Dual-mode Output Handler for Pre-commit Code Reviewer.

Detects interactive terminal vs agent context (!isatty or agent env vars).
Writes colored terminal output for humans AND updates the structured
.precommit-review.json file for AI agents to inspect and self-correct.
Provides thread/process-safe locking for parallel hook execution.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Ensure UTF-8 output on Windows consoles/pipes
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (OSError, ValueError):
        pass

if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (OSError, ValueError):
        pass

logger = logging.getLogger(__name__)

# ANSI Color Codes
COLOR_RESET = "\033[0m"
COLOR_BOLD = "\033[1m"
COLOR_RED = "\033[91m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_BLUE = "\033[94m"
COLOR_CYAN = "\033[96m"
COLOR_DIM = "\033[2m"

ICONS = {
    "pass": "[PASS]",
    "warn": "[WARN]",
    "fail": "[FAIL]",
    "info": "[INFO]",
    "qa": "[QA]",
    "security": "[SEC]",
    "hallucination": "[PLAN]",
}

REPORT_FILE_NAME = ".precommit-review.json"
LOCK_FILE_NAME = ".precommit-review.json.lock"


def safe_print(text: str = "") -> None:
    """Print text safely across different terminal encodings."""
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "ascii"
        clean = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
        try:
            print(clean)
        except OSError as err:
            logger.debug("safe_print fallback failed: %s", err)


def find_repo_root() -> Path:
    """Find repository root, fallback to current working directory."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return Path(proc.stdout.strip())
    except (OSError, subprocess.SubprocessError) as err:
        logger.debug("Failed to find git repo root: %s", err)
    return Path.cwd()


def get_current_branch() -> str:
    """Get current git branch name."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except (OSError, subprocess.SubprocessError) as err:
        logger.debug("Failed to find git current branch: %s", err)
    return "unknown"


def is_agent_mode() -> bool:
    """Detect if running in agent/non-interactive mode.

    Returns True if stdout is not a TTY or CI/ANTIGRAVITY/CODEX env vars are set.
    """
    if not sys.stdout.isatty():
        return True
    for env_key in ("CI", "ANTIGRAVITY", "CODEX"):
        if os.environ.get(env_key):
            return True
    return False


def supports_color() -> bool:
    """Check if terminal supports color and colors are not disabled."""
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


def colored(text: str, color_code: str) -> str:
    """Colorize text if color is supported."""
    if not supports_color():
        return text
    return f"{color_code}{text}{COLOR_RESET}"


def print_banner(check_name: str, description: str, icon: str = "") -> None:
    """Print check header banner."""
    prefix = f"{icon} " if icon else ""
    header = f"{prefix}[{check_name.upper()}] {description}"
    safe_print(colored(header, COLOR_BOLD + COLOR_CYAN))


def print_pass(message: str) -> None:
    """Print passing status."""
    safe_print(colored(f"{ICONS['pass']} {message}", COLOR_GREEN))


def print_warn(message: str) -> None:
    """Print warning status."""
    safe_print(colored(f"{ICONS['warn']} {message}", COLOR_YELLOW))


def print_fail(message: str) -> None:
    """Print failure status."""
    safe_print(colored(f"{ICONS['fail']} {message}", COLOR_RED + COLOR_BOLD))


def print_info(message: str) -> None:
    """Print informational status."""
    safe_print(colored(f"{ICONS['info']} {message}", COLOR_BLUE))


class FileLock:
    """Simple cross-platform file lock using lockfile creation."""

    def __init__(self, lock_path: Path, timeout: float = 10.0, retry_interval: float = 0.05):
        self.lock_path = lock_path
        self.timeout = timeout
        self.retry_interval = retry_interval
        self.acquired = False

    def __enter__(self):
        start = time.time()
        while time.time() - start < self.timeout:
            try:
                # O_CREAT | O_EXCL is atomic across platforms
                fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
                os.close(fd)
                self.acquired = True
                return self
            except (FileExistsError, OSError):
                time.sleep(self.retry_interval)

        # Timeout reached, force acquire by removing stale lock
        try:
            if self.lock_path.exists():
                self.lock_path.unlink()
            fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            os.close(fd)
            self.acquired = True
        except OSError as err:
            logger.debug("Forced lock acquire failed: %s", err)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.acquired:
            try:
                if self.lock_path.exists():
                    self.lock_path.unlink()
            except OSError as err:
                logger.debug("Lock release failed: %s", err)
            self.acquired = False


def _init_empty_report(staged_files: list[str] | None = None) -> dict[str, Any]:
    """Create an empty report structure."""
    return {
        "timestamp": datetime.now().astimezone().isoformat(),
        "commit_context": {
            "staged_files": staged_files or [],
            "branch": get_current_branch(),
        },
        "ai_backend_used": "skipped",
        "checks": {
            "qa": {"status": "pass", "findings": []},
            "security": {"status": "skipped", "findings": []},
            "hallucination": {"status": "skipped", "matched_plans": [], "findings": []},
        },
    }


def update_report(
    check_name: str,
    check_data: dict[str, Any],
    ai_backend_used: str | None = None,
    staged_files: list[str] | None = None,
) -> None:
    """Atomically update .precommit-review.json with findings from a check.

    Args:
        check_name: "qa", "security", or "hallucination".
        check_data: Dict conforming to the check's schema.
        ai_backend_used: "antigravity", "codex", "ollama", or "skipped".
        staged_files: Staged files list to update context.
    """
    repo_root = find_repo_root()
    report_file = repo_root / REPORT_FILE_NAME
    lock_file = repo_root / LOCK_FILE_NAME

    with FileLock(lock_file):
        report: dict[str, Any] = {}
        is_fresh = False

        if report_file.exists():
            try:
                with open(report_file, "r", encoding="utf-8") as f:
                    report = json.load(f)
                # Check age: if created within last 60 seconds, reuse to merge parallel checks
                ts_str = report.get("timestamp", "")
                if ts_str:
                    try:
                        ts = datetime.fromisoformat(ts_str)
                        age = (datetime.now().astimezone() - ts).total_seconds()
                        if 0 <= age <= 60:
                            is_fresh = True
                    except (ValueError, TypeError) as err:
                        logger.debug("Failed parsing report timestamp: %s", err)
            except (json.JSONDecodeError, OSError) as err:
                logger.debug("Failed reading existing report: %s", err)
                report = {}

        if not is_fresh or "checks" not in report:
            report = _init_empty_report(staged_files)

        # Merge check data
        if "checks" not in report:
            report["checks"] = {}
        report["checks"][check_name] = check_data

        # Update AI backend if used by this check
        if ai_backend_used and (
            ai_backend_used != "skipped"
            or report.get("ai_backend_used") in (None, "skipped")
        ):
            report["ai_backend_used"] = ai_backend_used

        # Merge staged files into commit_context
        if staged_files:
            existing_staged = report.get("commit_context", {}).get("staged_files", [])
            merged_files = sorted(set(existing_staged + staged_files))
            if "commit_context" not in report:
                report["commit_context"] = {}
            report["commit_context"]["staged_files"] = merged_files

        # Refresh timestamp
        report["timestamp"] = datetime.now().astimezone().isoformat()

        # Atomic write via temporary file
        temp_file = repo_root / f".precommit-review.tmp.{os.getpid()}"
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            temp_file.replace(report_file)
        except OSError as err:
            logger.debug("Atomic rename failed, falling back to direct write: %s", err)
            try:
                with open(report_file, "w", encoding="utf-8") as f:
                    json.dump(report, f, indent=2)
            except OSError as write_err:
                logger.warning("Failed writing pre-commit report: %s", write_err)
            finally:
                if temp_file.exists():
                    try:
                        temp_file.unlink()
                    except OSError as unlink_err:
                        logger.debug("Failed cleaning up temp report: %s", unlink_err)
