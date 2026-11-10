"""Deterministic QA Pre-commit Checks.

Executes deterministic quality checks on staged files:
1. python-lint: Run ruff check on staged Python files (blocking)
2. debug-artifacts: Detect console.log / debugger in non-test TS/JS (blocking)
3. merge-conflict-markers: Block unresolved git conflict markers (blocking)
4. print-in-services: Flag print() calls in service modules (blocking)
5. test-co-location: Warn if service modules lack a tests/ dir (non-blocking)
6. todo-markers: Warn on TODO/FIXME/HACK markers (non-blocking)
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Ensure scripts/precommit is on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from plan_matcher import normalize_path
from review_output import (
    find_repo_root,
    print_banner,
    print_fail,
    print_info,
    print_pass,
    print_warn,
    safe_print,
    update_report,
)

SCOPE_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx", ".py"}


def get_staged_files() -> list[str]:
    """Retrieve staged files from git diff --cached."""
    try:
        proc = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout:
            return [
                f.strip()
                for f in proc.stdout.splitlines()
                if f.strip()
            ]
    except (OSError, subprocess.SubprocessError) as err:
        logger.debug("Failed getting staged files: %s", err)
    return []


def is_test_file(path_str: str) -> bool:
    """Check if file is a test file."""
    norm = normalize_path(path_str).lower()
    return (
        ".test." in norm
        or ".spec." in norm
        or "/tests/" in norm
        or "/__tests__/" in norm
        or norm.startswith("tests/")
        or Path(norm).name.startswith("test_")
    )


def check_python_lint(py_files: list[str], repo_root: Path) -> list[dict[str, Any]]:
    """Run ruff check on python files, respecting per-service configs."""
    findings: list[dict[str, Any]] = []
    if not py_files:
        return findings

    if not (shutil.which("ruff") or shutil.which("ruff.exe")):
        print_warn("ruff not found on PATH. Skipping python lint check.")
        return findings

    # Group python files: service-specific vs general
    service_groups: dict[Path, list[str]] = {}
    general_files: list[str] = []

    for f in py_files:
        norm = normalize_path(f)
        parts = norm.split("/")
        if len(parts) >= 2 and parts[0] == "services":
            svc_dir = repo_root / parts[0] / parts[1]
            rel_to_svc = "/".join(parts[2:])
            service_groups.setdefault(svc_dir, []).append(rel_to_svc)
        else:
            general_files.append(norm)

    # Run ruff inside each service directory
    for svc_dir, files in service_groups.items():
        if not svc_dir.is_dir():
            continue
        try:
            cmd = ["ruff", "check", "--output-format", "json", *files]
            proc = subprocess.run(
                cmd,
                cwd=str(svc_dir),
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            if proc.stdout.strip():
                try:
                    diagnostics = json.loads(proc.stdout)
                    for diag in diagnostics:
                        filename = diag.get("filename", "")
                        # Relativize back to repo root
                        try:
                            rel_repo = normalize_path(str((svc_dir / filename).relative_to(repo_root)))
                        except (ValueError, OSError):
                            rel_repo = normalize_path(str(svc_dir / filename))

                        loc = diag.get("location", {})
                        line_no = loc.get("row", 1)
                        code = diag.get("code", "LINT")
                        msg = diag.get("message", "")
                        findings.append({
                            "rule": "python-lint",
                            "file": rel_repo,
                            "line": line_no,
                            "message": f"[{code}] {msg}",
                        })
                except json.JSONDecodeError:
                    if proc.returncode != 0:
                        findings.append({
                            "rule": "python-lint",
                            "file": str(svc_dir),
                            "line": 1,
                            "message": proc.stderr.strip() or proc.stdout.strip(),
                        })
        except (OSError, subprocess.SubprocessError) as e:
            print_warn(f"Failed to run ruff in {svc_dir}: {e}")

    # Run ruff for general root files
    if general_files:
        try:
            cmd = ["ruff", "check", "--output-format", "json", *general_files]
            proc = subprocess.run(
                cmd,
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            if proc.stdout.strip():
                try:
                    diagnostics = json.loads(proc.stdout)
                    for diag in diagnostics:
                        loc = diag.get("location", {})
                        findings.append({
                            "rule": "python-lint",
                            "file": normalize_path(diag.get("filename", "")),
                            "line": loc.get("row", 1),
                            "message": f"[{diag.get('code', 'LINT')}] {diag.get('message', '')}",
                        })
                except json.JSONDecodeError as err:
                    logger.debug("Failed parsing general ruff diagnostics: %s", err)
        except (OSError, subprocess.SubprocessError) as e:
            print_warn(f"Failed to run ruff on general files: {e}")

    return findings


def check_file_contents(
    files: list[str], repo_root: Path
) -> tuple[list[dict[str, Any]], list[str]]:
    """Scan file contents for debug artifacts, conflict markers, and print calls.

    Returns:
        (blocking_findings, warning_messages)
    """
    blocking_findings: list[dict[str, Any]] = []
    warnings: list[str] = []

    conflict_re = re.compile(r"^(<{7}|={7}|>{7})(?:\s.*)?$")
    debug_re = re.compile(r"\b(console\.log|debugger)\b")
    print_re = re.compile(r"^\s*print\s*\(")
    todo_re = re.compile(r"(?:#|//|/\*|\*)\s*(TODO|FIXME|HACK)\b")

    for file_str in files:
        file_path = repo_root / file_str
        if not file_path.is_file():
            continue

        ext = file_path.suffix.lower()
        norm = normalize_path(file_str)
        is_ts_js = ext in {".ts", ".tsx", ".js", ".jsx"}
        is_python = ext == ".py"
        is_service_python = is_python and norm.startswith("services/") and not is_test_file(norm)
        is_test = is_test_file(norm)

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except OSError as err:
            logger.debug("Failed opening file for content scan %s: %s", file_path, err)
            continue

        for idx, line in enumerate(lines, 1):
            # Check 1: Merge conflict markers (all files, blocking)
            if conflict_re.match(line):
                blocking_findings.append({
                    "rule": "merge-conflict-markers",
                    "file": norm,
                    "line": idx,
                    "message": "Unresolved merge conflict marker",
                })

            # Check 2: Debug artifacts in non-test TS/JS (blocking)
            if is_ts_js and not is_test:
                m = debug_re.search(line)
                if m:
                    blocking_findings.append({
                        "rule": "debug-artifacts",
                        "file": norm,
                        "line": idx,
                        "message": f"Found debug artifact: '{m.group(1)}'",
                    })

            # Check 3: Print calls in service python files (blocking)
            if is_service_python and print_re.search(line):
                blocking_findings.append({
                    "rule": "print-in-services",
                    "file": norm,
                    "line": idx,
                    "message": "print() call found in service code; use logging instead",
                })

            # Check 4: TODO/FIXME/HACK markers (non-blocking warning)
            m_todo = todo_re.search(line)
            if m_todo:
                warnings.append(f"[{m_todo.group(1)}] {norm}:{idx} - {line.strip()[:80]}")

    return blocking_findings, warnings


def check_test_colocation(files: list[str], repo_root: Path) -> list[str]:
    """Warn if service modules lack a tests/ directory."""
    warnings: list[str] = []
    checked_services = set()

    for file_str in files:
        norm = normalize_path(file_str)
        parts = norm.split("/")
        if len(parts) >= 2 and parts[0] == "services":
            svc_name = parts[1]
            if svc_name not in checked_services:
                checked_services.add(svc_name)
                svc_tests_dir = repo_root / "services" / svc_name / "tests"
                if not svc_tests_dir.is_dir():
                    warnings.append(
                        f"Service 'services/{svc_name}' lacks a tests/ directory."
                    )

    return warnings


def run_qa(files: list[str]) -> int:
    """Run all deterministic QA checks."""
    print_banner("qa", "Running deterministic code quality checks")
    repo_root = find_repo_root()

    scoped_files = [
        normalize_path(f)
        for f in files
        if Path(f).suffix.lower() in SCOPE_EXTENSIONS
    ]

    if not scoped_files:
        print_info("No files in scope for QA check.")
        update_report(
            "qa",
            {"status": "pass", "findings": []},
            staged_files=files,
        )
        return 0

    all_blocking_findings: list[dict[str, Any]] = []

    # 1. Python Lint (ruff)
    py_files = [f for f in scoped_files if f.endswith(".py")]
    lint_findings = check_python_lint(py_files, repo_root)
    all_blocking_findings.extend(lint_findings)

    # 2. Content scan (debug artifacts, conflict markers, print in services, TODOs)
    content_findings, todo_warnings = check_file_contents(scoped_files, repo_root)
    all_blocking_findings.extend(content_findings)

    # 3. Test co-location warnings
    colocation_warnings = check_test_colocation(scoped_files, repo_root)

    # Output non-blocking warnings
    all_warnings = todo_warnings + colocation_warnings
    if all_warnings:
        for w in all_warnings:
            print_warn(w)

    # Output blocking findings
    if all_blocking_findings:
        print_fail(f"QA check failed with {len(all_blocking_findings)} blocking issue(s):")
        for idx, finding in enumerate(all_blocking_findings, 1):
            rule = finding.get("rule", "unknown")
            file_path = finding.get("file", "unknown")
            line = finding.get("line", 1)
            msg = finding.get("message", "")
            safe_print(f"  {idx}. [{rule}] {file_path}:{line}: {msg}")

        update_report(
            "qa",
            {"status": "fail", "findings": all_blocking_findings},
            staged_files=scoped_files,
        )
        return 1

    print_pass("QA deterministic checks passed (ruff, debug artifacts, conflicts, logging clean)")
    update_report(
        "qa",
        {"status": "pass", "findings": []},
        staged_files=scoped_files,
    )
    return 0


def main() -> int:
    files = sys.argv[1:] if len(sys.argv) > 1 else get_staged_files()
    return run_qa(files)


if __name__ == "__main__":
    sys.exit(main())
