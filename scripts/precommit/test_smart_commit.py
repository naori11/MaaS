"""Unit tests for smart_commit.py."""

import re

from smart_commit import (
    CommitGroup,
    FileChange,
    generate_heuristic_message,
    group_files_semantically,
    matches_path_filters,
    normalize_path,
    parse_selection_indices,
    resolve_file_metadata,
    sanitize_header,
    should_ignore_file,
    wrap_text,
)

CONVENTIONAL_HEADER_REGEX = re.compile(
    r"^(feat|fix|docs|build|refactor|chore|ci|test|revert|perf)"
    r"(\([a-z0-9\-*]+\))?!?: "
    r"[a-z0-9][^\n]{0,68}[^.\s]$"
)


class TestPathNormalizationAndIgnore:
    def test_normalize_path(self):
        assert normalize_path(r"apps\web\page.tsx") == "apps/web/page.tsx"
        assert normalize_path("./services/billing/main.py") == "services/billing/main.py"
        assert normalize_path('"scripts/test.py"') == "scripts/test.py"

    def test_should_ignore_file(self):
        assert should_ignore_file(".precommit-review.json") is True
        assert should_ignore_file(".precommit-review.json.lock") is True
        assert should_ignore_file("scripts/precommit/__pycache__/ai.pyc") is True
        assert should_ignore_file(".turbo/cache.json") is True
        assert should_ignore_file(".pytest_cache/v/cache/node") is True
        assert should_ignore_file("node_modules/pkg/index.js") is True
        assert should_ignore_file("apps/web/page.tsx") is False
        assert should_ignore_file("services/billing/main.py") is False


class TestScopeResolution:
    def test_web_app_and_tests(self):
        scope, cat = resolve_file_metadata("apps/web/components/button.tsx")
        assert scope == "web"
        assert cat == "app"

        scope, cat = resolve_file_metadata("apps/web/components/button.test.tsx")
        assert scope == "web"
        assert cat == "test"

    def test_backend_services(self):
        scope, cat = resolve_file_metadata("services/billing/service.py")
        assert scope == "billing"
        assert cat == "service"

        scope, cat = resolve_file_metadata("services/billing/tests/test_service.py")
        assert scope == "billing"
        assert cat == "test"

        scope, cat = resolve_file_metadata("services/api-gateway/main.py")
        assert scope == "gateway"

        scope, cat = resolve_file_metadata("services/ledger/models.py")
        assert scope == "ledger"

        scope, cat = resolve_file_metadata("services/identity/jwt.py")
        assert scope == "identity"

        scope, cat = resolve_file_metadata("services/math-add/app.py")
        assert scope == "math-add"

    def test_scripts_and_docs(self):
        scope, cat = resolve_file_metadata("scripts/precommit/qa_check.py")
        assert scope == "precommit"
        assert cat == "chore"

        scope, cat = resolve_file_metadata("docs/architecture.md")
        assert scope == ""
        assert cat == "docs"

        scope, cat = resolve_file_metadata("package.json")
        assert scope == "build"

        scope, cat = resolve_file_metadata("pnpm-lock.yaml")
        assert scope == "deps"


class TestSemanticGrouping:
    def test_grouping_by_service_and_scope(self):
        changes = [
            FileChange(status="M", path="apps/web/page.tsx", scope="web", category="app"),
            FileChange(status="M", path="apps/web/page.test.tsx", scope="web", category="test"),
            FileChange(status="M", path="services/billing/main.py", scope="billing", category="service"),
            FileChange(status="M", path="services/billing/tests/test_main.py", scope="billing", category="test"),
            FileChange(status="M", path="README.md", scope="", category="docs"),
        ]

        groups = group_files_semantically(changes)
        group_keys = {g.group_id for g in groups}

        assert "scope_web" in group_keys
        assert "scope_billing" in group_keys
        assert "docs_all" in group_keys

        # Web group has both implementation and test
        web_group = next(g for g in groups if g.group_id == "scope_web")
        assert len(web_group.files) == 2
        assert web_group.scope == "web"

        # Billing group has both implementation and test
        billing_group = next(g for g in groups if g.group_id == "scope_billing")
        assert len(billing_group.files) == 2
        assert billing_group.scope == "billing"


class TestHeaderSanitization:
    def test_valid_formatting(self):
        h = sanitize_header("feat", "web", "add responsive navigation bar")
        assert h == "feat(web): add responsive navigation bar"
        assert CONVENTIONAL_HEADER_REGEX.match(h)

    def test_lowercase_enforcement(self):
        h = sanitize_header("fix", "billing", "Fix invalid transaction ID handling")
        assert h == "fix(billing): fix invalid transaction ID handling"
        assert CONVENTIONAL_HEADER_REGEX.match(h)

    def test_trailing_punctuation_removal(self):
        h = sanitize_header("docs", "", "update architecture documentation.")
        assert h == "docs: update architecture documentation"
        assert not h.endswith(".")
        assert CONVENTIONAL_HEADER_REGEX.match(h)

    def test_header_length_cap(self):
        long_subject = "a" * 100
        h = sanitize_header("feat", "gateway", long_subject)
        assert len(h) <= 72
        assert CONVENTIONAL_HEADER_REGEX.match(h)

    def test_invalid_type_fallback(self):
        h = sanitize_header("unknown_type", "ledger", "persist transaction")
        assert h.startswith("chore(ledger):")
        assert CONVENTIONAL_HEADER_REGEX.match(h)


class TestTextWrapping:
    def test_body_wrapping(self):
        long_paragraph = "word " * 30  # 150 characters
        wrapped = wrap_text(long_paragraph, max_line_len=100)
        lines = wrapped.splitlines()
        for line in lines:
            assert len(line) <= 100
        assert len(lines) > 1


class TestHeuristicGenerator:
    def test_heuristic_docs(self):
        group = CommitGroup(
            group_id="docs_all",
            scope="",
            category="docs",
            files=[FileChange(status="M", path="README.md", scope="", category="docs")],
        )
        header, body = generate_heuristic_message(group)
        assert header.startswith("docs:")
        assert CONVENTIONAL_HEADER_REGEX.match(header)
        assert "README.md" in body

    def test_heuristic_feature(self):
        group = CommitGroup(
            group_id="scope_web",
            scope="web",
            category="app",
            files=[FileChange(status="A", path="apps/web/new-view.tsx", scope="web", category="app")],
        )
        header, _ = generate_heuristic_message(group)
        assert header.startswith("feat(web):")
        assert CONVENTIONAL_HEADER_REGEX.match(header)


class TestSelectionAndFiltering:
    def test_parse_selection_all(self):
        assert parse_selection_indices("all", 5) == {1, 2, 3, 4, 5}
        assert parse_selection_indices("", 3) == {1, 2, 3}
        assert parse_selection_indices("yes", 4) == {1, 2, 3, 4}

    def test_parse_selection_explicit_numbers_and_ranges(self):
        assert parse_selection_indices("1, 3, 5", 5) == {1, 3, 5}
        assert parse_selection_indices("1-3, 5", 5) == {1, 2, 3, 5}
        assert parse_selection_indices("2", 4) == {2}

    def test_parse_selection_skip(self):
        assert parse_selection_indices("skip 2", 4) == {1, 3, 4}
        assert parse_selection_indices("-2", 4) == {1, 3, 4}
        assert parse_selection_indices("skip 1,3", 4) == {2, 4}

    def test_parse_selection_abort(self):
        assert parse_selection_indices("q", 5) == set()
        assert parse_selection_indices("abort", 5) == set()
        assert parse_selection_indices("n", 5) == set()

    def test_matches_path_filters(self):
        assert matches_path_filters("apps/web/page.tsx", ["apps/web"]) is True
        assert matches_path_filters("services/billing/main.py", ["services/billing/main.py"]) is True
        assert matches_path_filters("services/ledger/db.py", ["*.py"]) is True
        assert matches_path_filters("package.json", ["apps/web"]) is False
