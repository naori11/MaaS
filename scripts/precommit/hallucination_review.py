"""Hallucination Review Pre-commit Hook.

Compares staged changes against matched .planning/ plans.
Detects:
- endpoints/routes/API paths not mentioned in the plan
- data structures/contracts differing from plan specification
- files modified that are in the plan's "Forbidden files" list
- dependencies/imports not implied by the plan
- logic or behavior contradicting the plan's stated goals
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
from plan_matcher import find_matching_plans, normalize_path
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

SCOPE_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx", ".py"}


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
    """Filter files matching hallucination review scope."""
    scoped: list[str] = []
    for f in files:
        ext = Path(f).suffix.lower()
        if ext in SCOPE_EXTENSIONS:
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

    # Fallback to reading file content directly if diff is empty (e.g. testing)
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
    """Run hallucination review on given or staged files."""
    print_banner("hallucination", "Checking staged changes against planning specs")

    scoped_files = filter_scope(files)
    if not scoped_files:
        print_info("No files in scope for hallucination review.")
        update_report(
            "hallucination",
            {"status": "pass", "matched_plans": [], "findings": []},
            staged_files=files,
        )
        return 0

    matched_plans, plan_context = find_matching_plans(scoped_files)

    if not matched_plans:
        print_info("No matching plan found in .planning/ for staged files. Skipping hallucination check.")
        update_report(
            "hallucination",
            {"status": "no_plan_match", "matched_plans": [], "findings": []},
            staged_files=scoped_files,
        )
        return 0

    print_info(f"Matched plan(s): {', '.join(matched_plans)}")

    diff_text = get_diff_for_files(scoped_files)
    if not diff_text:
        print_pass("No changes detected to review.")
        update_report(
            "hallucination",
            {"status": "pass", "matched_plans": matched_plans, "findings": []},
            staged_files=scoped_files,
        )
        return 0

    system_prompt = (
        "You are an AI pre-commit code reviewer specializing in hallucination and scope control.\n"
        "Your task is to compare code changes against the approved plan specifications.\n\n"
        "Examine the code changes for:\n"
        "1. Endpoints, routes, or API paths not mentioned or authorized in the plan\n"
        "2. Data structures, contracts, or payloads differing from plan specifications\n"
        "3. Files modified that appear in the plan's 'Forbidden files' list\n"
        "4. Unplanned dependencies or unexpected imports not implied by the plan\n"
        "5. Logic, behavior, or features contradicting or deviating from stated goals\n\n"
        "You MUST respond ONLY with valid JSON conforming to this schema:\n"
        "{\n"
        '  "status": "pass" | "findings",\n'
        '  "findings": [\n'
        "    {\n"
        '      "severity": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW",\n'
        '      "file": "path/to/file",\n'
        '      "message": "Specific explanation of deviation or hallucination",\n'
        '      "plan_ref": "Section or excerpt from plan"\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "If there are no deviations or hallucinations, set status to 'pass' and findings to []."
    )

    user_prompt = (
        f"PLAN SPECIFICATIONS:\n\n{plan_context}\n\n"
        f"CODE CHANGES:\n\n{diff_text}\n\n"
        "Analyze the code changes against the plan specifications above. Return valid JSON."
    )

    print_info(f"Comparing changes against {len(matched_plans)} plan(s) via AI backend (typically 8-15s)...")
    raw_response, backend_used = generate(user_prompt, system=system_prompt)

    if not raw_response or backend_used == "skipped":
        print_warn("AI backend unavailable or timed out. Skipping hallucination review.")
        update_report(
            "hallucination",
            {"status": "skipped", "matched_plans": matched_plans, "findings": []},
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
            "hallucination",
            {"status": "skipped", "matched_plans": matched_plans, "findings": []},
            ai_backend_used=backend_used,
            staged_files=scoped_files,
        )
        return 0

    findings = parsed.get("findings", [])
    status = parsed.get("status", "pass")

    if status == "pass" or not findings:
        print_pass(f"Hallucination check passed via {backend_used} (matched plans: {', '.join(matched_plans)})")
        update_report(
            "hallucination",
            {"status": "pass", "matched_plans": matched_plans, "findings": []},
            ai_backend_used=backend_used,
            staged_files=scoped_files,
        )
        return 0

    print_warn(f"Hallucination review found {len(findings)} issue(s) via {backend_used}:")
    for idx, finding in enumerate(findings, 1):
        sev = finding.get("severity", "MEDIUM")
        file_path = finding.get("file", "unknown")
        msg = finding.get("message", "")
        plan_ref = finding.get("plan_ref", "")
        safe_print(f"  {idx}. [{sev}] {file_path}: {msg}")
        if plan_ref:
            safe_print(f"     Ref: {plan_ref}")

    update_report(
        "hallucination",
        {
            "status": "findings",
            "matched_plans": matched_plans,
            "findings": findings,
        },
        ai_backend_used=backend_used,
        staged_files=scoped_files,
    )

    strict_mode = os.environ.get("PRECOMMIT_AI_STRICT", "0") == "1"
    if strict_mode and not is_agent_mode():
        print_fail("Strict mode enabled: commit blocked due to hallucination review findings.")
        return 1

    return 0


def main() -> int:
    files = sys.argv[1:] if len(sys.argv) > 1 else get_staged_files()
    return run_review(files)


if __name__ == "__main__":
    sys.exit(main())
