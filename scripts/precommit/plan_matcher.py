"""Plan Matcher for Hallucination Review.

Discovers and matches .planning/ plan files (.md, .yml, .yaml) against staged file paths.
Parses plans for write sets, changes, forbidden files, goals, endpoints,
and data contracts to construct LLM context.
"""

from __future__ import annotations

import fnmatch
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

# Ensure scripts/precommit is on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

logger = logging.getLogger(__name__)

DEFAULT_PLANNING_DIR = ".planning"
SUPPORTED_EXTENSIONS = {".md", ".yml", ".yaml"}


def get_planning_dir() -> Path:
    """Resolve the planning directory path."""
    env_dir = os.environ.get("PLANNING_DIR", DEFAULT_PLANNING_DIR)
    path = Path(env_dir)
    if not path.is_absolute():
        from review_output import find_repo_root

        path = find_repo_root() / env_dir
    return path


def normalize_path(path: str) -> str:
    """Normalize file path to forward slashes without leading slashes or dots."""
    return path.strip().replace("\\", "/").removeprefix("./")


def file_matches_pattern(file_path: str, pattern: str) -> bool:
    """Check if a file path matches an exact path or a glob pattern."""
    norm_file = normalize_path(file_path)
    norm_pat = normalize_path(pattern)

    # Exact match
    if norm_file.lower() == norm_pat.lower():
        return True

    # Wildcard directory match: e.g. services/api-gateway/**
    if norm_pat.endswith("/**"):
        prefix = norm_pat[:-3]
        if norm_file.startswith(prefix + "/") or norm_file.lower() == prefix.lower():
            return True

    # Standard glob match
    return bool(
        ("*" in norm_pat or "?" in norm_pat)
        and fnmatch.fnmatch(norm_file.lower(), norm_pat.lower())
    )


def parse_plan_sections(content: str) -> dict[str, Any]:
    """Parse sections of a plan file (.md or .yml/.yaml)."""
    lines = content.splitlines()
    sections: dict[str, list[str]] = {}
    current_section = "header"
    sections[current_section] = []

    for line in lines:
        header_match = re.match(r"^#{1,3}\s+(.+)$", line)
        yaml_section_match = re.match(r"^([a-zA-Z0-9_\-]+):\s*$", line)

        if header_match:
            current_section = header_match.group(1).strip().lower()
            sections[current_section] = []
        elif yaml_section_match:
            current_section = yaml_section_match.group(1).strip().lower()
            sections[current_section] = []
        else:
            sections[current_section].append(line)

    write_set: set[str] = set()
    forbidden_files: set[str] = set()
    general_references: set[str] = set()

    file_regex = re.compile(
        r"`([^`]+)`|"
        r"[-*]\s+`([^`]+)`|"
        r"[-*]\s+([a-zA-Z0-9_\-./\\]+\.[a-zA-Z0-9]+)|"
        r"(?:path|script):\s*`?([a-zA-Z0-9_\-./\\]+\.[a-zA-Z0-9]+)`?"
    )

    for section_name, section_lines in sections.items():
        is_forbidden = "forbidden" in section_name
        is_write = any(
            k in section_name
            for k in (
                "write set",
                "target",
                "goal",
                "changes",
                "new_files",
                "modified_files",
                "plan",
            )
        )

        for line in section_lines:
            for m in file_regex.finditer(line):
                candidate = m.group(1) or m.group(2) or m.group(3) or m.group(4)
                if not candidate:
                    continue
                cand = normalize_path(candidate.strip())
                # Filter out pure markdown or non-file tokens
                if "/" in cand or "\\" in cand or re.search(
                    r"\.(?:ts|tsx|js|jsx|py|json|yml|yaml|env|toml|sh)$", cand
                ):
                    if is_forbidden:
                        forbidden_files.add(cand)
                    elif is_write:
                        write_set.add(cand)
                    else:
                        general_references.add(cand)

    return {
        "content": content,
        "write_set": write_set,
        "forbidden_files": forbidden_files,
        "general_references": general_references,
    }


def find_matching_plans(staged_files: list[str]) -> tuple[list[str], str]:
    """Find plan files in .planning/ (.md, .yml, .yaml) matching any staged file.

    Prioritizes plans where the staged files belong to the plan's write set,
    changes, or intended targets.

    Returns:
        (matched_plan_paths, combined_plan_context)
    """
    planning_dir = get_planning_dir()
    if not planning_dir.exists():
        return [], ""

    # Find all supported plan files (.md, .yml, .yaml)
    plan_files = sorted(
        [
            p
            for p in planning_dir.rglob("*")
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
        ]
    )
    from review_output import find_repo_root

    repo_root = find_repo_root()

    write_matched: list[tuple[str, str]] = []
    general_matched: list[tuple[str, str]] = []

    for plan_file in plan_files:
        try:
            rel_plan_path = normalize_path(str(plan_file.relative_to(repo_root)))
        except ValueError:
            rel_plan_path = normalize_path(str(plan_file))

        try:
            content = plan_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as err:
            logger.debug("Skipping unreadable plan file %s: %s", plan_file, err)
            continue

        parsed = parse_plan_sections(content)
        write_set = parsed["write_set"]
        general_refs = parsed["general_references"]

        has_write_match = False
        has_general_match = False

        for staged_file in staged_files:
            norm_staged = normalize_path(staged_file)
            for pat in write_set:
                if file_matches_pattern(norm_staged, pat):
                    has_write_match = True
                    break
            if not has_write_match:
                for pat in general_refs:
                    if file_matches_pattern(norm_staged, pat):
                        has_general_match = True
                        break

        plan_entry = (
            rel_plan_path,
            f"### Plan: {rel_plan_path}\n\n{content}\n",
        )

        if has_write_match:
            write_matched.append(plan_entry)
        elif has_general_match:
            general_matched.append(plan_entry)

    # Prefer write-set matches if available
    selected = write_matched if write_matched else general_matched
    matched_paths = [path for path, _ in selected]
    combined_context = "\n---\n".join([ctx for _, ctx in selected])

    return matched_paths, combined_context
