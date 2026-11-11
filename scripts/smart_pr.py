#!/usr/bin/env python3
"""Smart PR Automation Script for MaaS Monorepo.

Gathers git diff and commit context from the current branch vs the default branch,
generates a structured PR description via AI (or heuristic fallback) conforming to
.github/pull_request_template.md, and creates a draft PR using the GitHub CLI (gh).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# Paths setup
SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent
PRECOMMIT_DIR = SCRIPTS_DIR / "precommit"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(PRECOMMIT_DIR) not in sys.path:
    sys.path.insert(0, str(PRECOMMIT_DIR))

# Reuse UI and file metadata logic from smart_commit
try:
    from smart_commit import UI, resolve_file_metadata, run_git, should_ignore_file
except ImportError:
    class UI:  # type: ignore
        @classmethod
        def bold(cls, text: str) -> str:
            return text

        @classmethod
        def cyan(cls, text: str) -> str:
            return text

        @classmethod
        def green(cls, text: str) -> str:
            return text

        @classmethod
        def yellow(cls, text: str) -> str:
            return text

        @classmethod
        def red(cls, text: str) -> str:
            return text

        @classmethod
        def dim(cls, text: str) -> str:
            return text

    def run_git(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git"] + args,
            cwd=cwd or REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

    def resolve_file_metadata(path: str) -> tuple[str, str]:
        return "", "chore"

    def should_ignore_file(path: str) -> bool:
        return False

# Reuse AI backend abstraction
try:
    from precommit.ai_backend import generate, parse_json_response
except ImportError:
    generate = None  # type: ignore
    parse_json_response = None  # type: ignore


# ---------------------------------------------------------------------------
# Constants & AI System Prompt
# ---------------------------------------------------------------------------

AI_SYSTEM_PROMPT = """You are an expert software engineer generating a pull request description for the MaaS monorepo.
Analyze the provided git branch context, commits, and diff.

Generate a JSON object strictly matching this schema:
{
  "title": "feat(scope): concise description in conventional commits format",
  "what": [
    {
      "name": "Feature or Change Name",
      "description": "Plain English explanation of what it does for non-technical teammates"
    }
  ],
  "technical_details": [
    {
      "component": "Component or Service Name (e.g. Billing Service, Web, API Gateway)",
      "details": [
        "Technical detail explaining the implementation for developers",
        "Architecture decisions, algorithms, or patterns used"
      ]
    }
  ],
  "breaking_changes": [
    "Description of breaking change (leave array empty [] if none)"
  ],
  "how_to_test": [
    "pnpm --filter <service> test or pnpm test",
    "docker compose up -d --build (if services changed)",
    "Specific verification steps or curl commands"
  ],
  "related_issues": [
    "123"
  ]
}

Rules:
1. Title MUST follow Conventional Commits: <type>(<scope>): <description> (or <type>: <description> if root/global).
   Types: feat, fix, docs, build, refactor, chore, ci, test, revert, perf.
   Valid scopes: web, gateway, billing, ledger, identity, math-add, math-subtract, math-multiply, math-divide, nginx, deps, deps-dev, ci, docker, precommit.
2. The "what" section should be written in clear layman's terms.
3. Group "technical_details" by the services/components affected.
4. "breaking_changes" should be an empty list [] unless there are actual breaking changes.
5. "how_to_test" must provide concrete, actionable commands.
6. "related_issues" should list issue numbers as strings or ints (or empty list [] if none).
7. Respond ONLY with the JSON object. Do not wrap in markdown quotes if possible.
"""

COMPONENT_DISPLAY_NAMES = {
    "web": "Web Application (apps/web)",
    "gateway": "API Gateway",
    "billing": "Billing Service",
    "ledger": "Ledger Service",
    "identity": "Identity Service",
    "math-add": "Math Add Service",
    "math-subtract": "Math Subtract Service",
    "math-multiply": "Math Multiply Service",
    "math-divide": "Math Divide Service",
    "nginx": "Nginx Infrastructure",
    "precommit": "Pre-commit & Automation Scripts",
    "docker": "Docker Infrastructure",
    "ci": "CI / GitHub Actions",
    "build": "Build & Dependencies",
    "deps": "Dependencies",
}


# ---------------------------------------------------------------------------
# Preflight Functions
# ---------------------------------------------------------------------------

def find_gh_cli() -> str | None:
    """Find the path to the GitHub CLI (gh) executable."""
    which_path = shutil.which("gh") or shutil.which("gh.exe")
    if which_path:
        return which_path

    # Common Windows install locations
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    user_profile = os.environ.get("USERPROFILE", "")

    candidates = [
        Path(program_files) / "GitHub CLI" / "gh.exe",
        Path(program_files_x86) / "GitHub CLI" / "gh.exe",
        Path(local_app_data) / "Programs" / "GitHub CLI" / "gh.exe" if local_app_data else None,
        Path(user_profile) / "scoop" / "shims" / "gh.exe" if user_profile else None,
        Path("/usr/bin/gh"),
        Path("/usr/local/bin/gh"),
        Path("/opt/homebrew/bin/gh"),
    ]

    for candidate in candidates:
        if candidate and candidate.is_file():
            return str(candidate)

    return None


def check_gh_auth(gh_bin: str) -> bool:
    """Verify that gh CLI is authenticated."""
    try:
        proc = subprocess.run(
            [gh_bin, "auth", "status"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
        return proc.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def detect_default_branch() -> str:
    """Detect the repository default branch (master or main)."""
    proc = run_git(["symbolic-ref", "refs/remotes/origin/HEAD"])
    if proc.returncode == 0 and proc.stdout.strip():
        ref = proc.stdout.strip()
        return ref.split("/")[-1]

    proc_master = run_git(["rev-parse", "--verify", "origin/master"])
    if proc_master.returncode == 0:
        return "master"

    proc_main = run_git(["rev-parse", "--verify", "origin/main"])
    if proc_main.returncode == 0:
        return "main"

    for candidate in ("master", "main"):
        if run_git(["rev-parse", "--verify", candidate]).returncode == 0:
            return candidate

    return "master"


def get_current_branch() -> str:
    """Get the current checked-out git branch name."""
    proc = run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def check_uncommitted_changes() -> bool:
    """Check if there are any uncommitted changes in the working tree."""
    proc = run_git(["status", "--porcelain=v1"])
    if proc.returncode != 0:
        return False
    lines = [
        line for line in proc.stdout.splitlines()
        if line.strip() and not should_ignore_file(line[3:].strip())
    ]
    return len(lines) > 0


# ---------------------------------------------------------------------------
# Git Context Gathering
# ---------------------------------------------------------------------------

@dataclass
class ChangedFileInfo:
    path: str
    scope: str
    category: str


@dataclass
class PRContext:
    branch: str
    base: str
    base_ref: str
    commits_ahead: list[str]
    commits_count: int
    diff_stat: str
    diff_text: str
    changed_files: list[ChangedFileInfo]
    scopes: list[str]


def resolve_base_ref(base: str) -> str:
    """Resolve the git ref to compare against (origin/{base} if it exists, else {base})."""
    remote_ref = f"origin/{base}"
    proc = run_git(["rev-parse", "--verify", remote_ref])
    if proc.returncode == 0:
        return remote_ref
    return base


def gather_pr_context(base: str, current_branch: str | None = None) -> PRContext:
    """Gather commit messages, diff stat, diff snippet, and affected scopes."""
    branch = current_branch or get_current_branch()
    base_ref = resolve_base_ref(base)

    # 1. Commits ahead
    log_proc = run_git(["log", f"{base_ref}..HEAD", "--oneline"])
    commits_ahead = [line.strip() for line in log_proc.stdout.splitlines() if line.strip()]
    commits_count = len(commits_ahead)

    # 2. Diff stat
    stat_proc = run_git(["diff", f"{base_ref}..HEAD", "--stat"])
    diff_stat = stat_proc.stdout.strip()

    # 3. Full diff (truncated to ~6000 chars)
    diff_proc = run_git(["diff", f"{base_ref}..HEAD"])
    raw_diff = diff_proc.stdout.strip()
    max_diff_chars = 6000
    if len(raw_diff) > max_diff_chars:
        diff_text = raw_diff[:max_diff_chars] + "\n\n... [diff truncated for AI context]"
    else:
        diff_text = raw_diff

    # 4. Changed files & scopes
    names_proc = run_git(["diff", f"{base_ref}..HEAD", "--name-only"])
    changed_files: list[ChangedFileInfo] = []
    scopes_set: set[str] = set()

    for line in names_proc.stdout.splitlines():
        path = line.strip()
        if not path:
            continue
        scope, category = resolve_file_metadata(path)
        changed_files.append(ChangedFileInfo(path=path, scope=scope, category=category))
        if scope:
            scopes_set.add(scope)

    return PRContext(
        branch=branch,
        base=base,
        base_ref=base_ref,
        commits_ahead=commits_ahead,
        commits_count=commits_count,
        diff_stat=diff_stat,
        diff_text=diff_text,
        changed_files=changed_files,
        scopes=sorted(scopes_set),
    )


# ---------------------------------------------------------------------------
# PR Content Generation & Rendering
# ---------------------------------------------------------------------------

def derive_title_from_branch(branch: str, scopes: list[str]) -> str:
    """Derive conventional commit title heuristically from branch name and scopes."""
    b = branch.lower()

    # Map branch prefix to conventional type
    type_mapping = {
        "feature": "feat",
        "feat": "feat",
        "fix": "fix",
        "bugfix": "fix",
        "hotfix": "fix",
        "chore": "chore",
        "docs": "docs",
        "refactor": "refactor",
        "test": "test",
        "perf": "perf",
        "ci": "ci",
        "build": "build",
    }
    prefix_type = None
    for prefix, mapped in type_mapping.items():
        if b.startswith((f"{prefix}/", f"{prefix}-")):
            prefix_type = mapped
            b = b[len(prefix) + 1 :]
            break

    # Strip issue tokens like fix/123-something or issue-123
    b = re.sub(r"^(?:issue-|\d+-|#\d+-?)", "", b)

    # Detect scope from branch or files
    detected_scope = ""
    for s in scopes:
        if s and s in b:
            detected_scope = s
            break
    if not detected_scope and scopes:
        detected_scope = scopes[0]

    if not prefix_type:
        if any(word in b for word in ("fix", "bug", "patch", "repair")):
            prefix_type = "fix"
        elif any(word in b for word in ("test", "spec")):
            prefix_type = "test"
        elif any(word in b for word in ("doc", "note")):
            prefix_type = "docs"
        elif any(word in b for word in ("ci", "workflow", "action")):
            prefix_type = "ci"
        elif any(word in b for word in ("build", "dep", "package", "turbo")):
            prefix_type = "build"
        elif any(word in b for word in ("refactor", "clean")):
            prefix_type = "refactor"
        else:
            prefix_type = "feat"

    # Clean subject
    subject = b.replace("-", " ").replace("_", " ").strip()
    if detected_scope and subject.startswith(f"{detected_scope} "):
        subject = subject[len(detected_scope) + 1 :].strip()
    if not subject:
        subject = "automated updates"

    subject = subject[0].lower() + subject[1:]
    scope_part = f"({detected_scope})" if detected_scope else ""
    return f"{prefix_type}{scope_part}: {subject}"


def generate_heuristic_pr(ctx: PRContext, issue: str | None = None) -> dict:
    """Generate structured PR content without AI using git context."""
    title = derive_title_from_branch(ctx.branch, ctx.scopes)

    # What section
    what = []
    for c in ctx.commits_ahead:
        parts = c.split(" ", 1)
        msg = parts[1] if len(parts) > 1 else parts[0]
        if ":" in msg:
            name_part, desc_part = msg.split(":", 1)
            what.append({
                "name": name_part.strip(),
                "description": desc_part.strip(),
            })
        else:
            what.append({
                "name": "Change",
                "description": msg.strip(),
            })

    if not what:
        what.append({
            "name": "Updates",
            "description": f"Changes from {ctx.branch}",
        })

    # Technical details grouped by scope
    grouped: dict[str, list[str]] = {}
    for f in ctx.changed_files:
        scope_key = f.scope or "general"
        grouped.setdefault(scope_key, []).append(f.path)

    tech_details = []
    for s_key, file_list in grouped.items():
        comp_name = COMPONENT_DISPLAY_NAMES.get(s_key, s_key.title())
        details = [f"Update {p}" for p in file_list[:5]]
        if len(file_list) > 5:
            details.append(f"... and {len(file_list) - 5} more files")
        tech_details.append({
            "component": comp_name,
            "details": details,
        })

    # Test steps
    how_to_test = []
    for s in ctx.scopes:
        if s in ("web", "gateway", "billing", "ledger", "identity") or s.startswith("math-"):
            how_to_test.append(f"pnpm --filter {s} test")
    if not how_to_test:
        how_to_test.append("pnpm test")
    if any(f.category in ("service", "infra") for f in ctx.changed_files):
        how_to_test.append("docker compose up -d --build")
    how_to_test.append("Verify changed functionality and ensure all tests pass")

    # Related issues
    related_issues: list[str] = []
    if issue:
        related_issues.append(str(issue))
    else:
        branch_issue_match = re.search(r"(?:issue|fix|gh-)[/-]?(\d+)", ctx.branch)
        if branch_issue_match:
            related_issues.append(branch_issue_match.group(1))

    return {
        "title": title,
        "what": what,
        "technical_details": tech_details,
        "breaking_changes": [],
        "how_to_test": how_to_test,
        "related_issues": related_issues,
    }


def generate_ai_pr(
    ctx: PRContext,
    backend: str | None = None,
    timeout: int = 30,
    issue: str | None = None,
    verbose: bool = False,
) -> tuple[dict, bool, str]:
    """Generate PR data using AI with automatic fallback to heuristic generation."""
    if backend == "heuristic" or generate is None:
        return generate_heuristic_pr(ctx, issue=issue), False, "heuristic"

    commits_str = "\n".join(f"- {c}" for c in ctx.commits_ahead) if ctx.commits_ahead else "- (No commits)"
    files_str = "\n".join(f"- [{f.scope or 'root'}] {f.path}" for f in ctx.changed_files) if ctx.changed_files else "- (No files)"
    issue_str = f"\nRelated Issue: #{issue}" if issue else ""

    prompt = f"""Branch: {ctx.branch}
Target Base: {ctx.base}
Commits Ahead ({ctx.commits_count}):
{commits_str}

Files Changed ({len(ctx.changed_files)}):
{files_str}
{issue_str}

Git Diff Stat:
{ctx.diff_stat or '(empty)'}

Git Diff:
{ctx.diff_text or '(empty)'}
"""
    if verbose:
        print(f"\n{UI.dim('[VERBOSE] AI Prompt:')}\n{prompt[:1000]}...\n")

    resp, used_backend = generate(
        prompt,
        system=AI_SYSTEM_PROMPT,
        backend=backend,
        timeout=timeout,
    )

    if resp and parse_json_response is not None:
        data = parse_json_response(resp)
        if isinstance(data, dict) and "title" in data and "what" in data:
            if "technical_details" not in data or not isinstance(data["technical_details"], list):
                data["technical_details"] = []
            if "breaking_changes" not in data or not isinstance(data["breaking_changes"], list):
                data["breaking_changes"] = []
            if "how_to_test" not in data or not isinstance(data["how_to_test"], list):
                data["how_to_test"] = ["pnpm test"]
            if "related_issues" not in data or not isinstance(data["related_issues"], list):
                data["related_issues"] = []
            if issue and str(issue) not in [str(x) for x in data["related_issues"]]:
                data["related_issues"].append(str(issue))
            return data, True, used_backend

    fallback_data = generate_heuristic_pr(ctx, issue=issue)
    return fallback_data, False, "heuristic"


def render_pr_body(data: dict) -> str:
    """Render structured PR data into markdown matching .github/pull_request_template.md."""
    sections = []

    # 1. What does this PR do?
    sections.append("## What does this PR do?\n")
    what_items = data.get("what", [])
    if isinstance(what_items, list) and what_items:
        for item in what_items:
            if isinstance(item, dict):
                name = item.get("name", "Change")
                desc = item.get("description", "")
                sections.append(f"- **{name}**: {desc}")
            elif isinstance(item, str):
                sections.append(f"- {item}")
    else:
        sections.append("- General updates and improvements")
    sections.append("")

    # 2. Technical Details
    sections.append("## Technical Details\n")
    tech_items = data.get("technical_details", [])
    if isinstance(tech_items, list) and tech_items:
        for comp in tech_items:
            if isinstance(comp, dict):
                comp_name = comp.get("component", "General")
                sections.append(f"### {comp_name}")
                details = comp.get("details", [])
                if isinstance(details, list):
                    for d in details:
                        sections.append(f"- {d}")
                elif isinstance(details, str):
                    sections.append(f"- {details}")
                sections.append("")
            elif isinstance(comp, str):
                sections.append(f"- {comp}")
                sections.append("")
    else:
        sections.append("### General")
        sections.append("- Code updates\n")

    # 3. Breaking Changes
    sections.append("## Breaking Changes\n")
    breaking = data.get("breaking_changes", [])
    if isinstance(breaking, list) and breaking:
        for b in breaking:
            sections.append(f"- {b}")
    else:
        sections.append("- None")
    sections.append("")

    # 4. How to Test
    sections.append("## How to Test\n")
    test_steps = data.get("how_to_test", [])
    if isinstance(test_steps, list) and test_steps:
        for i, step in enumerate(test_steps, 1):
            sections.append(f"{i}. {step}")
    else:
        sections.append("1. `pnpm test`")
    sections.append("")

    # 5. Related Issues
    sections.append("## Related Issues\n")
    issues = data.get("related_issues", [])
    if isinstance(issues, list) and issues:
        for iss in issues:
            iss_clean = str(iss).strip().lstrip("#")
            sections.append(f"Closes #{iss_clean}")
    else:
        sections.append("Closes #")

    return "\n".join(sections).strip() + "\n"


# ---------------------------------------------------------------------------
# Terminal Preview & GitHub Execution
# ---------------------------------------------------------------------------

def print_pr_preview(
    ctx: PRContext,
    title: str,
    body: str,
    backend: str,
    draft: bool,
) -> None:
    """Print the terminal preview card for the PR."""
    box_width = 77
    pr_type = "Draft PR" if draft else "Ready for Review"
    ai_status = f"✓ Generated via {backend}" if backend != "heuristic" else "⚠ Heuristic fallback (no AI)"

    print(f"\n{UI.bold('┌' + '─' * box_width + '┐')}")
    print(f"{UI.bold('│')} 🚀 {UI.bold('SMART PR PREVIEW'):<73}{UI.bold('│')}")
    print(f"{UI.bold('├' + '─' * box_width + '┤')}")
    print(f"{UI.bold('│')}  {UI.bold('Branch:'):<10} {ctx.branch} → {ctx.base}")
    print(f"{UI.bold('│')}  {UI.bold('Title:'):<10} {UI.green(title)}")
    print(f"{UI.bold('│')}  {UI.bold('Type:'):<10} {UI.cyan(pr_type)}")
    print(f"{UI.bold('│')}  {UI.bold('Commits:'):<10} {ctx.commits_count} commit(s) ahead of {ctx.base}")
    print(f"{UI.bold('│')}  {UI.bold('AI:'):<10} {ai_status}")
    print(f"{UI.bold('├' + '─' * box_width + '┤')}")
    print(f"{UI.bold('│')}  {UI.bold('PR Body Preview:')}")
    for line in body.splitlines():
        print(f"{UI.bold('│')}  {line}")
    print(f"{UI.bold('└' + '─' * box_width + '┘')}\n")


def push_branch(branch: str) -> tuple[bool, str]:
    """Push branch to origin with tracking flag."""
    proc = run_git(["push", "-u", "origin", "HEAD"])
    if proc.returncode == 0:
        return True, proc.stdout.strip()
    return False, proc.stderr.strip() or proc.stdout.strip()


def create_pr(
    gh_bin: str,
    base: str,
    title: str,
    body: str,
    draft: bool = True,
) -> tuple[bool, str]:
    """Execute gh pr create and return success flag and PR URL or error string."""
    cmd = [
        gh_bin,
        "pr",
        "create",
        "--base",
        base,
        "--title",
        title,
        "--body",
        body,
    ]
    if draft:
        cmd.append("--draft")

    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if proc.returncode == 0:
        return True, proc.stdout.strip()
    return False, proc.stderr.strip() or proc.stdout.strip()


# ---------------------------------------------------------------------------
# CLI Argument Parser & Main Entrypoint
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Smart PR Automation: Create draft pull requests with AI-generated descriptions."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview PR title and body without pushing or creating PR.",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip confirmation prompt and create PR immediately.",
    )
    parser.add_argument(
        "--draft",
        dest="draft",
        action="store_true",
        default=True,
        help="Create as draft PR (default).",
    )
    parser.add_argument(
        "--no-draft",
        dest="draft",
        action="store_false",
        help="Create as ready-for-review PR (not draft).",
    )
    parser.add_argument(
        "--base",
        type=str,
        default=None,
        help="Override target base branch (default: auto-detected, e.g. master/main).",
    )
    parser.add_argument(
        "--backend",
        type=str,
        default="auto",
        help="Force AI backend: auto, antigravity, codex, ollama, heuristic (default: auto).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="AI backend timeout in seconds (default: 30s).",
    )
    parser.add_argument(
        "--title",
        type=str,
        default=None,
        help="Override generated PR title.",
    )
    parser.add_argument(
        "--issue",
        type=str,
        default=None,
        help="Link to GitHub issue number.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON instead of formatted text.",
    )
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="Skip 'git push' before creating PR (assume branch already pushed).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show full diff and verbose AI details.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    # 1. Preflight checks
    gh_bin = find_gh_cli()
    if not gh_bin:
        print(f"{UI.red('[ERROR]')} GitHub CLI ('gh') is not installed or not found on PATH.", file=sys.stderr)
        print("Install it from: https://cli.github.com/ or run 'winget install --id GitHub.cli'", file=sys.stderr)
        return 1

    if not check_gh_auth(gh_bin):
        print(f"{UI.red('[ERROR]')} GitHub CLI ('gh') is not authenticated.", file=sys.stderr)
        print("Run 'gh auth login' to authenticate.", file=sys.stderr)
        return 1

    current_branch = get_current_branch()
    base = args.base or detect_default_branch()

    if current_branch == base:
        if args.json:
            print(json.dumps({"error": f"Already on '{base}', nothing to PR.", "status": "skipped"}))
        else:
            print(f"[INFO] Already on '{base}', nothing to PR.")
        return 0

    if check_uncommitted_changes():
        print(f"{UI.yellow('[WARN]')} You have uncommitted changes in your working tree.", file=sys.stderr)
        print(f"       The PR will only cover committed changes ahead of '{base}'.\n", file=sys.stderr)

    # 2. Gather git context
    ctx = gather_pr_context(base=base, current_branch=current_branch)
    if ctx.commits_count == 0:
        if args.json:
            print(json.dumps({"error": f"Branch '{ctx.branch}' is up to date with '{ctx.base}', nothing to PR.", "status": "skipped"}))
        else:
            print(f"[INFO] Branch '{ctx.branch}' is up to date with '{ctx.base}', nothing to PR.")
        return 0

    # 3. AI-generate PR description
    data, _ai_ok, backend_used = generate_ai_pr(
        ctx,
        backend=args.backend,
        timeout=args.timeout,
        issue=args.issue,
        verbose=args.verbose,
    )
    title = args.title or data.get("title", f"feat: {ctx.branch}")
    body = render_pr_body(data)

    # 4. JSON output (preview or non-interactive)
    payload = {
        "branch": ctx.branch,
        "base": ctx.base,
        "draft": args.draft,
        "title": title,
        "body": body,
        "backend": backend_used,
        "data": data,
    }
    if args.json and (args.dry_run or not args.yes):
        print(json.dumps(payload, indent=2))
        return 0

    # 5. Render & Preview
    if not args.json:
        print_pr_preview(ctx, title=title, body=body, backend=backend_used, draft=args.draft)

    if args.dry_run:
        print(f"{UI.green('[DRY-RUN]')} Preview finished. No PR was created.")
        return 0

    # 6. Interactive confirmation
    if not args.yes:
        prompt_text = "Create this draft PR? [Y/n/edit]: " if args.draft else "Create this PR? [Y/n/edit]: "
        try:
            ans = input(prompt_text).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n[ABORT] PR creation cancelled by user.")
            return 1

        if ans in ("n", "no", "q", "abort", "cancel"):
            print("[ABORT] PR creation cancelled by user. No PR created.")
            return 0

        if ans == "edit":
            custom_title = input(f"New title [{title}]: ").strip()
            if custom_title:
                title = custom_title
            print(f"[INFO] Updated title: {title}")
            try:
                ans2 = input("Proceed with PR creation? [Y/n]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\n[ABORT] PR creation cancelled by user.")
                return 1
            if ans2 in ("n", "no", "q", "abort", "cancel"):
                print("[ABORT] PR creation cancelled by user. No PR created.")
                return 0

    # 7. Push branch
    if not args.no_push:
        if not args.json:
            print(f"[INFO] Pushing branch '{ctx.branch}' to origin...")
        push_ok, push_err = push_branch(ctx.branch)
        if not push_ok:
            if args.json:
                payload["error"] = f"Failed to push branch '{ctx.branch}' to origin: {push_err}"
                payload["success"] = False
                print(json.dumps(payload, indent=2))
            else:
                print(f"{UI.red('[ERROR]')} Failed to push branch '{ctx.branch}' to origin:\n{push_err}", file=sys.stderr)
            return 1

    # 8. Create PR
    pr_type_str = "draft " if args.draft else ""
    if not args.json:
        print(f"[INFO] Creating {pr_type_str}pull request...")
    pr_ok, pr_out = create_pr(gh_bin, base=ctx.base, title=title, body=body, draft=args.draft)

    if args.json:
        payload["url"] = pr_out if pr_ok else None
        payload["error"] = pr_out if not pr_ok else None
        payload["success"] = pr_ok
        print(json.dumps(payload, indent=2))
        return 0 if pr_ok else 1

    if pr_ok:
        print(f"\n{UI.green('[SUCCESS]')} Pull Request created successfully!")
        print(f"URL: {pr_out}\n")
        return 0
    else:
        print(f"\n{UI.red('[ERROR]')} Failed to create PR:\n{pr_out}\n", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
