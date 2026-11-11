#!/usr/bin/env python3
"""Smart Commit Automation Script for MaaS Monorepo.

Analyzes modified files in the working tree, groups them logically by monorepo
domain/scope, generates conventional commit messages (1-liner + detailed body)
using AI (Antigravity/Codex/Ollama) with deterministic fallback, and commits
each group atomically via git subprocess.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Add scripts and precommit directory to path to import precommit modules
SCRIPTS_DIR = Path(__file__).resolve().parent
PRECOMMIT_DIR = SCRIPTS_DIR / "precommit"
REPO_ROOT = SCRIPTS_DIR.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(PRECOMMIT_DIR) not in sys.path:
    sys.path.insert(0, str(PRECOMMIT_DIR))

try:
    from precommit.ai_backend import generate, parse_json_response, select_backend
except ImportError:
    generate = None  # type: ignore
    parse_json_response = None  # type: ignore
    select_backend = lambda: None  # type: ignore


# ---------------------------------------------------------------------------
# UI & Color Styling
# ---------------------------------------------------------------------------

class UI:
    """Terminal styling and formatted card output."""

    ENABLE_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")

    @classmethod
    def color(cls, text: str, code: str) -> str:
        return f"{code}{text}\033[0m" if cls.ENABLE_COLOR else text

    @classmethod
    def bold(cls, text: str) -> str:
        return cls.color(text, "\033[1m")

    @classmethod
    def dim(cls, text: str) -> str:
        return cls.color(text, "\033[2m")

    @classmethod
    def cyan(cls, text: str) -> str:
        return cls.color(text, "\033[36m")

    @classmethod
    def green(cls, text: str) -> str:
        return cls.color(text, "\033[32m")

    @classmethod
    def yellow(cls, text: str) -> str:
        return cls.color(text, "\033[33m")

    @classmethod
    def red(cls, text: str) -> str:
        return cls.color(text, "\033[31m")

    @classmethod
    def magenta(cls, text: str) -> str:
        return cls.color(text, "\033[35m")

    @classmethod
    def badge(cls, status: str) -> str:
        s = status.strip()
        if "M" in s:
            return cls.color("[MODIFIED]", "\033[36m")
        if "A" in s or "?" in s:
            return cls.color("[NEW]     ", "\033[32m")
        if "D" in s:
            return cls.color("[DELETED] ", "\033[31m")
        if "R" in s:
            return cls.color("[RENAMED] ", "\033[33m")
        return cls.color("[CHANGED] ", "\033[35m")


# ---------------------------------------------------------------------------
# Constants & Conventional Commits Rules
# ---------------------------------------------------------------------------

ALLOWED_TYPES = [
    "feat",
    "fix",
    "docs",
    "build",
    "refactor",
    "chore",
    "ci",
    "test",
    "revert",
    "perf",
]

ALLOWED_SCOPES = [
    "web",
    "gateway",
    "billing",
    "ledger",
    "identity",
    "math-add",
    "math-subtract",
    "math-multiply",
    "math-divide",
    "nginx",
    "deps",
    "deps-dev",
    "ci",
    "docker",
    "precommit",
]

HEADER_MAX_LENGTH = 72
BODY_MAX_LINE_LENGTH = 100

IGNORED_PATTERNS = [
    r"^\.precommit-review\.",
    r"(^|/)\.pytest_cache($|/)",
    r"(^|/)\.ruff_cache($|/)",
    r"(^|/)__pycache__($|/)",
    r"(^|/)\.turbo($|/)",
    r"(^|/)node_modules($|/)",
    r"(^|/)\.obsidian($|/)",
    r"(^|/)\.smart-env($|/)",
    r"(^|/)repomix-output\.",
    r"\.tfstate(\.backup)?$",
    r"\.py[cod]$",
    r"\.DS_Store$",
    r"Thumbs\.db$",
    r"\.bak$",
    r"\.tmp$",
    r"\.swp$",
]


@dataclass
class FileChange:
    status: str  # 'M', 'A', 'D', 'R', '??'
    path: str
    scope: str
    category: str  # 'service', 'app', 'test', 'docs', 'infra', 'build', 'chore'


@dataclass
class CommitGroup:
    group_id: str
    scope: str
    category: str = "chore"
    files: list[FileChange] = field(default_factory=list)
    header: str = ""
    body: str = ""
    commit_type: str = "chore"


# ---------------------------------------------------------------------------
# Scope & Category Resolver
# ---------------------------------------------------------------------------

def normalize_path(path: str) -> str:
    """Normalize file path to forward slashes relative to repo root."""
    p = path.replace("\\", "/").strip().strip('"').strip("'")
    return p.removeprefix("./")


def matches_path_filters(path: str, filters: list[str]) -> bool:
    """Check if a normalized path matches any of the given path/glob filters."""
    if not filters:
        return True
    norm_path = normalize_path(path).lower()
    for flt in filters:
        norm_flt = normalize_path(flt).lower()
        if norm_flt == norm_path:
            return True
        if norm_path.startswith(norm_flt.rstrip("/") + "/"):
            return True
        if fnmatch.fnmatch(norm_path, norm_flt) or fnmatch.fnmatch(norm_path, f"*/{norm_flt}"):
            return True
        if norm_flt in norm_path:
            return True
    return False


def parse_selection_indices(input_str: str, total_count: int) -> set[int]:
    """Parse user selection string into a set of 1-based indices.

    Supports:
        "all", "y", "yes", "" -> all indices {1..total_count}
        "1, 3, 5" or "1 3 5" -> {1, 3, 5}
        "1-3, 5" -> {1, 2, 3, 5}
        "skip 2", "skip 2,4", "-2", "-2,4" -> all minus {2, 4}
        "q", "n", "abort", "none", "cancel" -> set()
    """
    raw = input_str.strip().lower()
    if not raw or raw in ("all", "y", "yes"):
        return set(range(1, total_count + 1))
    if raw in ("q", "n", "no", "abort", "none", "cancel"):
        return set()

    is_skip = False
    if raw.startswith(("skip ", "skip:")):
        is_skip = True
        raw = raw.split(" ", 1)[-1] if " " in raw else raw.split(":", 1)[-1]
    elif raw.startswith("-"):
        is_skip = True
        raw = raw.lstrip("-")

    selected: set[int] = set()
    tokens = re.split(r"[,\s]+", raw)
    for token in tokens:
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            parts = token.split("-")
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                start, end = int(parts[0]), int(parts[1])
                if start <= end:
                    selected.update(range(start, end + 1))
                else:
                    selected.update(range(end, start + 1))
        elif token.isdigit():
            selected.add(int(token))

    valid_selected = {i for i in selected if 1 <= i <= total_count}
    if is_skip:
        return set(range(1, total_count + 1)) - valid_selected
    return valid_selected


def should_ignore_file(path: str) -> bool:
    """Check if file matches ignore patterns."""
    norm = normalize_path(path)
    for pattern in IGNORED_PATTERNS:
        if re.search(pattern, norm):
            return True
    return False


def resolve_file_metadata(path: str) -> tuple[str, str]:
    """Resolve the canonical scope and category for a file path.

    Returns:
        (scope, category)
    """
    norm = normalize_path(path)

    # Apps
    if norm.startswith("apps/web/"):
        if ".test." in norm or "/__tests__/" in norm or "/tests/" in norm:
            return "web", "test"
        return "web", "app"

    # Services
    if norm.startswith("services/api-gateway/"):
        if "/tests/" in norm or "test_" in norm:
            return "gateway", "test"
        return "gateway", "service"
    if norm.startswith("services/billing/"):
        if "/tests/" in norm or "test_" in norm:
            return "billing", "test"
        return "billing", "service"
    if norm.startswith("services/ledger/"):
        if "/tests/" in norm or "test_" in norm:
            return "ledger", "test"
        return "ledger", "service"
    if norm.startswith("services/identity/"):
        if "/tests/" in norm or "test_" in norm:
            return "identity", "test"
        return "identity", "service"
    if norm.startswith("services/math-add/"):
        return "math-add", "test" if "test" in norm else "service"
    if norm.startswith("services/math-subtract/"):
        return "math-subtract", "test" if "test" in norm else "service"
    if norm.startswith("services/math-multiply/"):
        return "math-multiply", "test" if "test" in norm else "service"
    if norm.startswith("services/math-divide/"):
        return "math-divide", "test" if "test" in norm else "service"
    if norm.startswith("services/nginx/"):
        return "nginx", "infra"

    # Scripts & Precommit
    if norm.startswith("scripts/precommit/"):
        return "precommit", "test" if "test_" in norm else "chore"
    if norm.startswith("scripts/"):
        return "chore", "chore"

    # CI / CD & Workflows
    if norm.startswith(".github/"):
        return "ci", "infra"

    # Infrastructure & Docker
    if (
        norm.startswith("infra/")
        or "docker-compose" in norm
        or "Dockerfile" in norm
        or norm.endswith((".tf", ".tfstate"))
    ):
        return "docker" if "docker" in norm else "ci", "infra"

    # Documentation & Planning
    if (
        norm.startswith(("docs/", ".docs/", ".planning/", "self-study/"))
        or norm.endswith((".md", ".pkt"))
    ):
        return "", "docs"

    # Build & Dependencies
    if norm in (
        "package.json",
        "pnpm-lock.yaml",
        "pnpm-workspace.yaml",
        "turbo.json",
        "commitlint.config.js",
        "lefthook.yml",
    ):
        if "lock" in norm:
            return "deps", "build"
        return "build", "build"

    return "", "chore"


# ---------------------------------------------------------------------------
# Git State Collection
# ---------------------------------------------------------------------------

def run_git(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Execute git command and return CompletedProcess."""
    return subprocess.run(
        ["git"] + args,
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def unstage_all(cwd: Path | None = None) -> bool:
    """Safely unstage all staged files from the git index without modifying the working tree."""
    head_proc = run_git(["rev-parse", "--verify", "HEAD"], cwd=cwd)
    if head_proc.returncode == 0:
        proc = run_git(["restore", "--staged", "."], cwd=cwd)
    else:
        proc = run_git(["rm", "--cached", "-r", "."], cwd=cwd)
    return proc.returncode == 0


def get_changed_files(
    staged_only: bool = False,
    include_untracked: bool = True,
    path_filters: list[str] | None = None,
    scope_filter: str | None = None,
) -> list[FileChange]:
    """Collect modified, added, deleted, and untracked files from git with optional filtering."""
    proc = run_git(["status", "--porcelain=v1", "-uall"])
    if proc.returncode != 0:
        print(f"[ERROR] Failed to run git status: {proc.stderr}", file=sys.stderr)
        return []

    changes: list[FileChange] = []
    for line in proc.stdout.splitlines():
        if not line or len(line) < 3:
            continue

        status_code = line[:2]
        file_path = line[3:].strip()

        # Handle renamed files: R  old -> new
        if " -> " in file_path:
            file_path = file_path.split(" -> ")[-1].strip()

        file_path = normalize_path(file_path)

        if should_ignore_file(file_path):
            continue

        staged = status_code[0] not in (" ", "?")
        is_untracked = status_code == "??"

        if staged_only and not staged:
            continue
        if not include_untracked and is_untracked:
            continue

        if path_filters and not matches_path_filters(file_path, path_filters):
            continue

        scope, category = resolve_file_metadata(file_path)

        if scope_filter and scope.lower() != scope_filter.lower():
            continue

        changes.append(
            FileChange(
                status=status_code.strip(),
                path=file_path,
                scope=scope,
                category=category,
            )
        )

    return changes


def prompt_pick_files(changes: list[FileChange]) -> list[FileChange]:
    """Display an interactive file picker and return the selected subset."""
    print(f"\n{UI.bold('┌─────────────────────────────────────────────────────────────────────────────┐')}")
    print(f"{UI.bold('│')} 📋 {UI.bold('SELECT FILES TO COMMIT')} ({len(changes)} changed files available)                         {UI.bold('│')}")
    print(f"{UI.bold('└─────────────────────────────────────────────────────────────────────────────┘')}\n")

    for idx, change in enumerate(changes, 1):
        badge = UI.badge(change.status)
        scope_str = f"({UI.cyan(change.scope)})" if change.scope else f"({UI.dim('general')})"
        print(f"  [{idx:2d}] {badge} {scope_str:<18} {change.path}")

    print(f"\n{UI.dim('Tip: Enter comma-separated numbers (e.g. 1, 3, 5), range (1-4), or press Enter for all.')}")
    try:
        selection = input(f"Select file numbers to commit [{UI.green('all')}]: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n[ABORT] Selection cancelled.")
        return []

    selected_indices = parse_selection_indices(selection, len(changes))
    if not selected_indices:
        print("[INFO] No files selected.")
        return []

    selected_changes = [changes[i - 1] for i in sorted(selected_indices) if 1 <= i <= len(changes)]
    print(f"\n[INFO] Selected {len(selected_changes)} of {len(changes)} file(s).\n")
    return selected_changes


def get_git_diff_summary(files: list[str], max_chars: int = 3000) -> str:
    """Get summarized diff for a list of files."""
    if not files:
        return ""
    proc = run_git(["diff", "HEAD", "--"] + files)
    output = proc.stdout
    if not output:
        # Check if they are untracked
        proc_untracked = run_git(["diff", "--no-index", "/dev/null"] + files[:1])
        output = proc_untracked.stdout or ""

    if len(output) > max_chars:
        return output[:max_chars] + f"\n... [diff truncated, total length: {len(output)} chars]"
    return output


# ---------------------------------------------------------------------------
# Semantic Grouping Algorithm
# ---------------------------------------------------------------------------

def group_files_semantically(changes: list[FileChange]) -> list[CommitGroup]:
    """Cluster file changes into logical, atomic commit groups."""
    groups_map: dict[str, CommitGroup] = {}

    for change in changes:
        # Determine group identifier
        if change.scope:
            group_key = f"scope_{change.scope}"
            group_scope = change.scope
            group_category = change.category
        elif change.category == "docs":
            group_key = "docs_all"
            group_scope = ""
            group_category = "docs"
        elif change.category == "build":
            group_key = "build_config"
            group_scope = ""
            group_category = "build"
        elif change.category == "infra":
            group_key = "infra_ci"
            group_scope = "ci"
            group_category = "infra"
        else:
            group_key = "general_chore"
            group_scope = ""
            group_category = "chore"

        if group_key not in groups_map:
            groups_map[group_key] = CommitGroup(
                group_id=group_key,
                scope=group_scope,
                category=group_category,
            )

        groups_map[group_key].files.append(change)

    return list(groups_map.values())


# ---------------------------------------------------------------------------
# Conventional Commit Formatting & Validation
# ---------------------------------------------------------------------------

def wrap_text(text: str, max_line_len: int = BODY_MAX_LINE_LENGTH) -> str:
    """Wrap lines at word boundaries without breaking words."""
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            lines.append("")
            continue
        words = paragraph.split(" ")
        current_line: list[str] = []
        current_len = 0
        for word in words:
            if current_len + len(word) + (1 if current_line else 0) <= max_line_len:
                current_line.append(word)
                current_len += len(word) + (1 if current_len > 0 else 0)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
                current_len = len(word)
        if current_line:
            lines.append(" ".join(current_line))
    return "\n".join(lines)


def sanitize_header(commit_type: str, scope: str, subject: str) -> str:
    """Sanitize and format header to strictly satisfy commitlint rules."""
    c_type = commit_type.strip().lower()
    if c_type not in ALLOWED_TYPES:
        c_type = "chore"

    c_scope = scope.strip().lower()
    if c_scope and c_scope not in ALLOWED_SCOPES and not c_scope.startswith("math-"):
        c_scope = ""

    # Subject cleaning: lowercase first character, strip trailing punctuation
    c_subj = subject.strip()
    if c_subj:
        c_subj = c_subj[0].lower() + c_subj[1:]
    c_subj = re.sub(r"[.!\s]+$", "", c_subj)

    scope_part = f"({c_scope})" if c_scope else ""
    prefix = f"{c_type}{scope_part}: "
    max_subj_len = HEADER_MAX_LENGTH - len(prefix)

    if len(c_subj) > max_subj_len:
        c_subj = c_subj[:max_subj_len].rstrip()

    return f"{prefix}{c_subj}"


def generate_heuristic_message(group: CommitGroup) -> tuple[str, str]:
    """Generate conventional commit message deterministically when AI is unavailable."""
    paths = [f.path for f in group.files]
    categories = {f.category for f in group.files}
    statuses = {f.status for f in group.files}

    # Determine commit type
    if group.scope == "deps":
        c_type = "build"
        subj = "update dependencies"
    elif group.category == "docs" or all(f.category == "docs" for f in group.files):
        c_type = "docs"
        if any("study" in p for p in paths):
            subj = "update study notes and documentation"
        else:
            subj = "update project documentation"
    elif categories == {"test"}:
        c_type = "test"
        subj = f"add tests for {group.scope or 'components'}"
    elif group.scope == "precommit":
        c_type = "feat" if any("??" in f.status or "A" in f.status for f in group.files) else "fix"
        subj = "update pre-commit review configuration"
    elif group.category == "build":
        c_type = "build"
        subj = "update monorepo configuration"
    elif any("??" in s or "A" in s for s in statuses):
        c_type = "feat"
        subj = f"add {group.scope or 'features'}"
    elif any("D" in s for s in statuses):
        c_type = "refactor"
        subj = f"remove unused files from {group.scope or 'project'}"
    else:
        c_type = "fix" if "service" in categories or "app" in categories else "chore"
        subj = f"update {group.scope or 'project files'}"

    header = sanitize_header(c_type, group.scope, subj)
    body_lines = ["Changes included:"]
    for f in group.files[:8]:
        body_lines.append(f"- {f.path}")
    if len(group.files) > 8:
        body_lines.append(f"- ... and {len(group.files) - 8} more files")

    body = wrap_text("\n".join(body_lines))
    return header, body


# ---------------------------------------------------------------------------
# AI Commit Message Generation
# ---------------------------------------------------------------------------

AI_SYSTEM_PROMPT = """You are an automated Git Commit Message Generator for the MaaS repository.
Your output must strictly adhere to the project's Conventional Commits specification:

Format:
<type>(<scope>): <subject>

[optional body]

Rules:
1. Type must be one of: feat, fix, docs, build, refactor, chore, ci, test, revert, perf
2. Scope must be one of: web, gateway, billing, ledger, identity, math-add, math-subtract, math-multiply, math-divide, nginx, deps, deps-dev, ci, docker, precommit (or omitted if none applies)
3. Header (type + scope + colon + subject) MUST NOT exceed 72 characters.
4. Subject MUST be in lowercase, imperative mood ("add", not "added" or "adds"), and have NO trailing period.
5. Body must explain WHAT changed and WHY, wrapping lines at 100 characters max.
6. Return ONLY valid JSON in this exact structure:
{
  "type": "feat",
  "scope": "web",
  "subject": "add checkout error boundary",
  "body": "Wrap checkout button with recovery state to handle fatal network drops."
}
"""


def generate_ai_message(
    group: CommitGroup, backend: str | None = None, timeout: int = 20
) -> tuple[str, str, bool, str]:
    """Generate commit message using AI backend with validation and fallback.

    Returns:
        (header, body, ai_succeeded, used_backend)
    """
    if not generate:
        header, body = generate_heuristic_message(group)
        return header, body, False, "heuristic"

    file_paths = [f.path for f in group.files]
    diff_summary = get_git_diff_summary(file_paths, max_chars=2500)

    prompt = f"""Generate a Conventional Commit message for the following file changes:

Target Scope: {group.scope or 'None'}
Files changed:
{chr(10).join(f"- [{f.status}] {f.path}" for f in group.files)}

Git Diff summary:
{diff_summary}
"""

    try:
        raw_resp, used_backend = generate(
            prompt=prompt,
            system=AI_SYSTEM_PROMPT,
            backend=backend,
            timeout=timeout,
        )

        if raw_resp:
            parsed = parse_json_response(raw_resp)
            if parsed and isinstance(parsed, dict) and "subject" in parsed:
                c_type = str(parsed.get("type", "chore"))
                c_scope = str(parsed.get("scope", group.scope))
                c_subj = str(parsed.get("subject", ""))
                c_body = str(parsed.get("body", ""))

                header = sanitize_header(c_type, c_scope, c_subj)
                body = wrap_text(c_body) if c_body else ""
                return header, body, True, used_backend
    except (subprocess.SubprocessError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[WARN] AI message generation failed ({exc}), falling back to heuristic", file=sys.stderr)

    header, body = generate_heuristic_message(group)
    return header, body, False, "heuristic"


# ---------------------------------------------------------------------------
# Commit Execution & Hook Monitoring
# ---------------------------------------------------------------------------

def print_summary_table(groups: list[CommitGroup]) -> None:
    """Print a clean, compact, tabular overview of all proposed commit groups."""
    total_files = sum(len(g.files) for g in groups)
    title = f" 📦 SMART COMMIT PLAN ({len(groups)} group(s), {total_files} file(s)) "
    box_width = 86

    print(f"\n┌{title.center(box_width - 2, '─')}┐")
    print(f"│ {'#':<3} │ {'Scope':<12} │ {'Files':<6} │ {'Proposed Commit Header':<56} │")
    print(f"├{'─' * 5}┼{'─' * 14}┼{'─' * 8}┼{'─' * 58}┤")

    for idx, g in enumerate(groups, 1):
        scope_str = g.scope if g.scope else "general"
        files_str = str(len(g.files))
        header_str = g.header
        if len(header_str) > 55:
            header_str = header_str[:52] + "..."
        print(f"│ {idx:<3} │ {scope_str:<12} │ {files_str:>5} │ {header_str:<56} │")

    print(f"└{'─' * 5}┴{'─' * 14}┴{'─' * 8}┴{'─' * 58}┘\n")


def print_group_card(group: CommitGroup, index: int, total: int, verbose: bool = False) -> None:
    """Print a beautifully formatted visual card for a commit group."""
    scope_label = UI.cyan(group.scope) if group.scope else UI.dim("general / root")
    file_count = len(group.files)
    file_label = f"{file_count} file" if file_count == 1 else f"{file_count} files"

    header_text = f"[{index}/{total}] Group: {group.group_id} ({file_label})"
    print(f"\n┌─ 📦 {UI.bold(header_text)} " + "─" * max(5, 75 - len(header_text)))
    print(f"│  {UI.bold('Scope:')}  {scope_label}")
    print(f"│  {UI.bold('Header:')} {UI.green(group.header)}")
    if group.body:
        body_lines = group.body.splitlines()
        print(f"│  {UI.bold('Body:')}   {body_lines[0]}")
        for bl in body_lines[1:3]:
            print(f"│          {bl}")
        if len(body_lines) > 3:
            print(f"│          {UI.dim('...')}")
    print(f"│  {UI.bold('Files:')}")

    max_preview_files = 6 if not verbose else len(group.files)
    for f in group.files[:max_preview_files]:
        badge = UI.badge(f.status)
        print(f"│    • {badge} {f.path}")

    if len(group.files) > max_preview_files:
        remaining = len(group.files) - max_preview_files
        print(f"│    {UI.dim(f'... and {remaining} more files (use --verbose to show all)')}")

    print(f"└{'─' * 76}")


def execute_commit(group: CommitGroup, dry_run: bool = False) -> bool:
    """Stage files and commit atomically for a group."""
    file_paths = [f.path for f in group.files]

    if dry_run:
        return True

    print(f"\n{UI.bold('┌─ 🚀 Committing Group:')} {UI.cyan(group.group_id)}")
    print(f"│  Header: {UI.green(group.header)}")
    print(f"│  Staging {len(file_paths)} file(s)...")

    # 1. Ensure staging index has no pre-staged files to guarantee atomic isolation
    unstage_all()

    # 2. Stage files for this group
    add_proc = run_git(["add", "--"] + file_paths)
    if add_proc.returncode != 0:
        print(f"│  {UI.red('[ERROR] Failed to stage files:')} {add_proc.stderr}", file=sys.stderr)
        print(f"└{'─' * 60}")
        return False

    # 3. Verify changes were actually staged for this group
    diff_proc = run_git(["diff", "--cached", "--name-only"])
    staged = [f.strip() for f in diff_proc.stdout.splitlines() if f.strip()]
    if not staged:
        print(f"│  {UI.yellow('[WARN] No staged changes detected for this group (files may already be committed). Skipping.')}")
        print(f"└{'─' * 60}")
        return True

    # 4. Commit files
    commit_args = ["commit", "-m", group.header]
    if group.body:
        commit_args.extend(["-m", group.body])

    commit_proc = run_git(commit_args)

    if commit_proc.returncode != 0:
        print(f"│  {UI.red('[ERROR] Git commit failed:')}\n{commit_proc.stderr or commit_proc.stdout}", file=sys.stderr)
        print(f"│  {UI.yellow('[INFO] Rolling back staged changes for this group...')}", file=sys.stderr)
        unstage_all()
        print(f"└{'─' * 60}")
        return False

    print(f"│  {UI.green('[SUCCESS]')} Committed successfully!")

    # 5. Check .precommit-review.json if created
    review_file = REPO_ROOT / ".precommit-review.json"
    if review_file.is_file():
        try:
            review_data = json.loads(review_file.read_text(encoding="utf-8"))
            status = review_data.get("overall_status", "pass")
            print(f"│  [HOOKS] Pre-commit review status: {status}")
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as err:
            print(f"│  {UI.dim(f'[HOOKS] Could not read .precommit-review.json: {err}')}")

    print(f"└{'─' * 60}")
    return True


# ---------------------------------------------------------------------------
# Main CLI Entrypoint
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Smart Commit Automation: Group files and commit atomically with conventional messages."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Optional specific files or directory paths to include in the commit.",
    )
    parser.add_argument(
        "--scope",
        type=str,
        default=None,
        help="Only commit changes within a specific scope (e.g. web, billing, gateway).",
    )
    parser.add_argument(
        "--pick",
        "--select",
        action="store_true",
        dest="pick_files",
        help="Interactively select specific files to commit from a list.",
    )
    parser.add_argument(
        "--groups",
        type=str,
        default=None,
        help="Comma-separated list or range of group numbers to commit (e.g. --groups 1,3 or 1-3).",
    )
    parser.add_argument(
        "--skip-groups",
        type=str,
        default=None,
        help="Comma-separated list or range of group numbers to skip (e.g. --skip-groups 2).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Display all files in group cards without truncation.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview proposed commit groups and messages without modifying git state.",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Non-interactive execution (skip confirmation prompts).",
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Step-by-step confirmation per commit group.",
    )
    parser.add_argument(
        "--staged-only",
        action="store_true",
        help="Only process currently staged changes.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
        help="Timeout in seconds for AI backend calls (default: 20s).",
    )
    parser.add_argument(
        "--backend",
        type=str,
        default=None,
        help="Force AI backend: auto, antigravity, codex, ollama, heuristic.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON results.",
    )

    args = parser.parse_args()

    # Step 1: Detect changes
    path_filters = args.paths if args.paths else None
    changes = get_changed_files(
        staged_only=args.staged_only,
        path_filters=path_filters,
        scope_filter=args.scope,
    )
    if not changes:
        print("[INFO] No modified, staged, or untracked files matching criteria.")
        return 0

    # Optional interactive file selection
    if args.pick_files:
        changes = prompt_pick_files(changes)
        if not changes:
            return 0

    print(f"[INFO] Discovered {len(changes)} changed file(s).")

    # Step 2: Group changes
    groups = group_files_semantically(changes)
    print(f"[INFO] Clustered into {len(groups)} atomic commit group(s).")

    # Early group filtering if CLI flags specified
    if args.groups:
        selected_indices = parse_selection_indices(args.groups, len(groups))
        groups = [g for i, g in enumerate(groups, 1) if i in selected_indices]
        print(f"[INFO] Filtered to {len(groups)} group(s) via --groups.")
    elif args.skip_groups:
        skip_indices = parse_selection_indices(args.skip_groups, len(groups))
        groups = [g for i, g in enumerate(groups, 1) if i not in skip_indices]
        print(f"[INFO] Filtered to {len(groups)} group(s) via --skip-groups.")

    if not groups:
        print("[INFO] No groups remain after filtering.")
        return 0

    # Step 3: Generate commit messages
    active_backend = args.backend
    for i, group in enumerate(groups, 1):
        print(f"[INFO] ({i}/{len(groups)}) Analyzing changes and generating message for {group.group_id}...", flush=True)
        if active_backend == "heuristic":
            header, body = generate_heuristic_message(group)
        else:
            header, body, ai_ok, used_backend = generate_ai_message(group, backend=active_backend, timeout=args.timeout)
            if not ai_ok:
                print("[INFO] AI backend unavailable; switching to heuristic generator for remaining groups.", flush=True)
                active_backend = "heuristic"
            elif active_backend is None and used_backend not in ("antigravity", "skipped", "heuristic", None):
                active_backend = used_backend
                print(f"[INFO] Primary AI backend switched to '{used_backend}' for remaining groups.", flush=True)

        group.header = header
        group.body = body

    if args.json:
        output_payload = [
            {
                "group_id": g.group_id,
                "scope": g.scope,
                "header": g.header,
                "body": g.body,
                "files": [f.path for f in g.files],
            }
            for g in groups
        ]
        print(json.dumps(output_payload, indent=2))
        if args.dry_run:
            return 0

    # Step 4: Summary Table
    print_summary_table(groups)

    if args.dry_run:
        for idx, group in enumerate(groups, 1):
            print_group_card(group, idx, len(groups), verbose=args.verbose)
        print(f"\n{UI.green('[DRY-RUN]')} Finished preview. No git changes were made.")
        return 0

    # Step 5: Manual Approval & Selection of Groups
    selected_group_indices: set[int] = set(range(1, len(groups) + 1))
    step_by_step = args.interactive

    if args.groups:
        selected_group_indices = parse_selection_indices(args.groups, len(groups))
    elif args.skip_groups:
        skip_indices = parse_selection_indices(args.skip_groups, len(groups))
        selected_group_indices = set(range(1, len(groups) + 1)) - skip_indices
    elif not args.yes:
        print(f"{UI.bold('Options:')}")
        print(f"  • Press {UI.green('Enter')} or type {UI.green('all')} to commit all {len(groups)} groups")
        print(f"  • Enter group numbers to commit only those (e.g. {UI.cyan('1, 3')} or {UI.cyan('1-3')})")
        print(f"  • Skip specific groups (e.g. {UI.yellow('skip 1')} or {UI.yellow('-1')})")
        print(f"  • Type {UI.cyan('i')} for step-by-step interactive review (approve/edit/skip each)")
        print(f"  • Type {UI.red('q')} to abort\n")

        try:
            user_input = input(f"Select action [{UI.green('all')}]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n[ABORT] Commit process cancelled by user.")
            return 1

        if user_input in ("q", "n", "no", "abort", "cancel"):
            print("[ABORT] Commit process cancelled by user. No files were committed.")
            return 0
        elif user_input in ("i", "interactive"):
            step_by_step = True
        elif user_input:
            selected_group_indices = parse_selection_indices(user_input, len(groups))
            if not selected_group_indices:
                print("[ABORT] No groups selected for commit. No files were committed.")
                return 0

    # Step 6: Filter and execute commits
    groups_to_commit = [
        (idx, group)
        for idx, group in enumerate(groups, 1)
        if idx in selected_group_indices
    ]

    if len(groups_to_commit) < len(groups):
        skipped_count = len(groups) - len(groups_to_commit)
        print(f"[INFO] Committing {len(groups_to_commit)} group(s); skipping {skipped_count} group(s).")

    # Unstage any pre-staged files to ensure each group commits in total isolation
    unstage_all()

    all_success = True
    for idx, group in groups_to_commit:
        if step_by_step:
            print_group_card(group, idx, len(groups), verbose=args.verbose)
            try:
                ans = input("Proceed with this commit? [Y/n/edit]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\n[ABORT] Cancelled.")
                break

            if ans == "edit":
                custom_header = input(f"New header [{group.header}]: ").strip()
                if custom_header:
                    group.header = sanitize_header(group.commit_type, group.scope, custom_header)
            elif ans in ("n", "no", "skip"):
                print(f"[SKIP] Skipping group '{group.group_id}'.")
                continue

        success = execute_commit(group, dry_run=False)
        if not success:
            all_success = False
            print("[HALT] Aborting remaining groups due to commit failure.")
            break

    return 0 if all_success else 1


if __name__ == "__main__":
    sys.exit(main())
