"""Security Review Pre-commit Hook.

Scans staged diffs for security anti-patterns and vulnerabilities:
- hardcoded secrets, API keys, tokens, passwords
- SQL injection (raw string interpolation in queries)
- XSS vectors (dangerouslySetInnerHTML, unescaped user input)
- SSRF or open redirect patterns
- overly permissive CORS (Access-Control-Allow-Origin: *)
- exposed internal service URLs (should stay behind gateway)
- missing auth/authz checks on new endpoints
- insecure crypto (MD5, SHA1 for security, weak random)
- path traversal vulnerabilities
- sensitive data in logs (passwords, tokens, PII)
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Ensure scripts/precommit is on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ai_backend import generate, parse_json_response
from plan_matcher import normalize_path
from review_output import (
    is_agent_mode,
    print_banner,
    print_fail,
    print_info,
    print_pass,
    print_warn,
    safe_print,
    update_report,
)

SCOPE_EXTENSIONS = {
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".py",
    ".yml",
    ".yaml",
    ".json",
    ".env",
}


def get_staged_files() -> list[str]:
    """Retrieve staged files from git diff --cached."""
    try:
        proc = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
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


def filter_scope(files: list[str]) -> list[str]:
    """Filter files matching security review scope."""
    scoped: list[str] = []
    for f in files:
        ext = Path(f).suffix.lower()
        # Also include .env* files
        name = Path(f).name.lower()
        if ext in SCOPE_EXTENSIONS or name.startswith(".env"):
            scoped.append(normalize_path(f))
    return scoped


def get_diff_for_files(files: list[str]) -> str:
    """Get git diff for the specified files."""
    try:
        proc = subprocess.run(
            ["git", "--no-pager", "diff", "--cached", "--", *files],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()

        # Fallback to diff against HEAD
        proc = subprocess.run(
            ["git", "diff", "HEAD", "--", *files],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except (OSError, subprocess.SubprocessError) as err:
        logger.debug("Failed git diff for files: %s", err)

    content_snippets = []
    for f in files:
        p = Path(f)
        if p.is_file():
            try:
                snippet = p.read_text(encoding="utf-8")[:4000]
                content_snippets.append(f"--- File: {f} ---\n{snippet}")
            except (OSError, UnicodeDecodeError) as err:
                logger.debug("Failed reading snippet for %s: %s", f, err)
    return "\n\n".join(content_snippets)


def run_review(files: list[str]) -> int:
    """Run security review on given or staged files."""
    print_banner("security", "Scanning code changes for security vulnerabilities")

    scoped_files = filter_scope(files)
    if not scoped_files:
        print_info("No files in scope for security review.")
        update_report(
            "security",
            {"status": "pass", "findings": []},
            staged_files=files,
        )
        return 0

    diff_text = get_diff_for_files(scoped_files)
    if not diff_text:
        print_pass("No changes detected to review.")
        update_report(
            "security",
            {"status": "pass", "findings": []},
            staged_files=scoped_files,
        )
        return 0

    system_prompt = (
        "You are an expert Application Security Pre-commit Code Reviewer.\n"
        "Analyze the provided code diff / changes for security vulnerabilities and anti-patterns, specifically:\n"
        "1. Hardcoded secrets, API keys, tokens, passwords, private keys\n"
        "2. SQL injection (e.g. raw string concatenation/interpolation in SQL queries)\n"
        "3. Cross-Site Scripting (XSS) vectors (dangerouslySetInnerHTML, unescaped HTML)\n"
        "4. SSRF (Server-Side Request Forgery) or open redirect patterns\n"
        "5. Overly permissive CORS (e.g. Access-Control-Allow-Origin: * on authenticated routes)\n"
        "6. Exposed internal service URLs that should remain private behind the API gateway\n"
        "7. Missing authentication or authorization checks on newly added endpoints\n"
        "8. Insecure cryptography (MD5, SHA1 for security hashes, weak random generators)\n"
        "9. Path traversal vulnerabilities (user input in file paths without sanitization)\n"
        "10. Sensitive data leaking in log statements (passwords, tokens, PII)\n\n"
        "You MUST respond ONLY with valid JSON conforming strictly to this schema:\n"
        "{\n"
        '  "status": "pass" | "findings",\n'
        '  "findings": [\n'
        "    {\n"
        '      "severity": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW",\n'
        '      "file": "path/to/file",\n'
        '      "message": "Clear explanation of the security vulnerability and remediation"\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "If there are no security vulnerabilities or concerns, set status to 'pass' and findings to []."
    )

    user_prompt = (
        f"STAGED CODE CHANGES:\n\n{diff_text}\n\n"
        "Review these changes for security anti-patterns. Return valid JSON only."
    )

    print_info(f"Analyzing {len(scoped_files)} file(s) via AI backend (typically 8-15s)...")
    raw_response, backend_used = generate(user_prompt, system=system_prompt)

    if not raw_response or backend_used == "skipped":
        print_warn("AI backend unavailable or timed out. Skipping security review.")
        update_report(
            "security",
            {"status": "skipped", "findings": []},
            ai_backend_used="skipped",
            staged_files=scoped_files,
        )
        strict_mode = os.environ.get("PRECOMMIT_AI_STRICT", "0") == "1"
        if strict_mode and not is_agent_mode():
            print_fail("Strict mode enabled: commit blocked due to AI backend unavailability or timeout.")
            return 1
        return 0

    parsed = parse_json_response(raw_response)
    if not parsed or "status" not in parsed:
        print_warn(f"Failed to parse AI backend ({backend_used}) response as JSON. Skipping.")
        update_report(
            "security",
            {"status": "skipped", "findings": []},
            ai_backend_used=backend_used,
            staged_files=scoped_files,
        )
        return 0

    findings = parsed.get("findings", [])
    status = parsed.get("status", "pass")

    if status == "pass" or not findings:
        print_pass(f"Security review passed via {backend_used} (0 issues found)")
        update_report(
            "security",
            {"status": "pass", "findings": []},
            ai_backend_used=backend_used,
            staged_files=scoped_files,
        )
        return 0

    print_warn(f"Security review found {len(findings)} issue(s) via {backend_used}:")
    for idx, finding in enumerate(findings, 1):
        sev = finding.get("severity", "MEDIUM")
        file_path = finding.get("file", "unknown")
        msg = finding.get("message", "")
        safe_print(f"  {idx}. [{sev}] {file_path}: {msg}")

    update_report(
        "security",
        {
            "status": "findings",
            "findings": findings,
        },
        ai_backend_used=backend_used,
        staged_files=scoped_files,
    )

    strict_mode = os.environ.get("PRECOMMIT_AI_STRICT", "0") == "1"
    if strict_mode and not is_agent_mode():
        print_fail("Strict mode enabled: commit blocked due to security review findings.")
        return 1

    return 0


def main() -> int:
    files = sys.argv[1:] if len(sys.argv) > 1 else get_staged_files()
    return run_review(files)


if __name__ == "__main__":
    sys.exit(main())
