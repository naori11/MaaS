"""Unit tests for smart_pr.py."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from smart_pr import (
    ChangedFileInfo,
    PRContext,
    check_gh_auth,
    derive_title_from_branch,
    find_gh_cli,
    generate_ai_pr,
    generate_heuristic_pr,
    main,
    parse_args,
    render_pr_body,
)


class TestCliPathAndAuth:
    def test_find_gh_cli_found(self):
        with patch("shutil.which", return_value="C:\\dummy\\gh.exe"):
            assert find_gh_cli() == "C:\\dummy\\gh.exe"

    def test_find_gh_cli_candidates(self, tmp_path):
        gh_mock = tmp_path / "gh.exe"
        gh_mock.write_text("mock binary")

        with (
            patch("shutil.which", return_value=None),
            patch("os.environ.get", return_value=str(tmp_path)),
            patch("pathlib.Path.is_file", return_value=True),
        ):
            result = find_gh_cli()
            assert result is not None

    def test_check_gh_auth_success(self):
        mock_proc = MagicMock(returncode=0)
        with patch("subprocess.run", return_value=mock_proc):
            assert check_gh_auth("gh") is True

    def test_check_gh_auth_failure(self):
        mock_proc = MagicMock(returncode=1)
        with patch("subprocess.run", return_value=mock_proc):
            assert check_gh_auth("gh") is False


class TestBranchAndTitleDerivation:
    def test_derive_title_with_prefixes(self):
        assert derive_title_from_branch("feature/billing-retry", ["billing"]) == "feat(billing): retry"
        assert derive_title_from_branch("fix/gateway-timeout", ["gateway"]) == "fix(gateway): timeout"
        assert derive_title_from_branch("docs/update-readme", ["docs"]) == "docs(docs): update readme"
        assert derive_title_from_branch("chore/clean-logs", ["chore"]) == "chore(chore): clean logs"

    def test_derive_title_without_prefix(self):
        assert derive_title_from_branch("billing-webhook", ["billing"]) == "feat(billing): webhook"
        assert derive_title_from_branch("pr-automation", ["precommit"]) == "feat(precommit): pr automation"

    def test_derive_title_with_issue_number(self):
        assert derive_title_from_branch("fix/123-null-pointer", ["web"]) == "fix(web): null pointer"


class TestHeuristicGeneration:
    def test_heuristic_pr_structure(self):
        ctx = PRContext(
            branch="billing-webhook",
            base="master",
            base_ref="origin/master",
            commits_ahead=["abc1234 feat(billing): add webhook retry logic"],
            commits_count=1,
            diff_stat="services/billing/main.py | 10 ++++++++++",
            diff_text="diff --git a/services/billing/main.py...",
            changed_files=[
                ChangedFileInfo(path="services/billing/main.py", scope="billing", category="service")
            ],
            scopes=["billing"],
        )

        data = generate_heuristic_pr(ctx, issue="42")
        assert "feat(billing)" in data["title"]
        assert len(data["what"]) == 1
        assert "feat(billing)" in data["what"][0]["name"]
        assert "retry logic" in data["what"][0]["description"]
        assert len(data["technical_details"]) == 1
        assert "Billing Service" in data["technical_details"][0]["component"]
        assert "pnpm --filter billing test" in data["how_to_test"]
        assert "42" in data["related_issues"]


class TestTemplateRendering:
    def test_render_pr_body_formatting(self):
        data = {
            "title": "feat(billing): add subscription retry logic",
            "what": [
                {
                    "name": "Subscription retry",
                    "description": "Automatically retries failed Xendit charges",
                }
            ],
            "technical_details": [
                {
                    "component": "Billing Service",
                    "details": [
                        "Add RetryPolicy dataclass with configurable max_attempts",
                        "Wire retry loop into webhook handler",
                    ],
                }
            ],
            "breaking_changes": [],
            "how_to_test": [
                "pnpm --filter billing test",
                "docker compose up -d --build",
            ],
            "related_issues": ["99"],
        }

        rendered = render_pr_body(data)
        assert "## What does this PR do?" in rendered
        assert "- **Subscription retry**: Automatically retries failed Xendit charges" in rendered
        assert "## Technical Details" in rendered
        assert "### Billing Service" in rendered
        assert "- Add RetryPolicy dataclass with configurable max_attempts" in rendered
        assert "## Breaking Changes" in rendered
        assert "- None" in rendered
        assert "## How to Test" in rendered
        assert "1. pnpm --filter billing test" in rendered
        assert "2. docker compose up -d --build" in rendered
        assert "## Related Issues" in rendered
        assert "Closes #99" in rendered

    def test_render_pr_body_empty_issues(self):
        data = {
            "what": [{"name": "Feature", "description": "Desc"}],
            "technical_details": [{"component": "Web", "details": ["Detail"]}],
            "breaking_changes": [],
            "how_to_test": ["pnpm test"],
            "related_issues": [],
        }
        rendered = render_pr_body(data)
        assert "Closes #" in rendered


class TestAIGenerationAndFallback:
    def test_ai_generation_success(self):
        ctx = PRContext(
            branch="feature/test",
            base="master",
            base_ref="origin/master",
            commits_ahead=["123 commit"],
            commits_count=1,
            diff_stat="stat",
            diff_text="diff",
            changed_files=[],
            scopes=[],
        )

        mock_payload = {
            "title": "feat(web): new button component",
            "what": [{"name": "Button", "description": "Added new button"}],
            "technical_details": [{"component": "Web", "details": ["Added button.tsx"]}],
            "breaking_changes": [],
            "how_to_test": ["pnpm test"],
            "related_issues": [],
        }

        with patch("smart_pr.generate", return_value=(json.dumps(mock_payload), "antigravity")):
            data, ok, backend = generate_ai_pr(ctx, backend="antigravity")
            assert ok is True
            assert backend == "antigravity"
            assert data["title"] == "feat(web): new button component"

    def test_ai_generation_fallback_on_failure(self):
        ctx = PRContext(
            branch="fix/ledger-sync",
            base="master",
            base_ref="origin/master",
            commits_ahead=["123 commit"],
            commits_count=1,
            diff_stat="stat",
            diff_text="diff",
            changed_files=[ChangedFileInfo(path="services/ledger/sync.py", scope="ledger", category="service")],
            scopes=["ledger"],
        )

        with patch("smart_pr.generate", return_value=(None, "skipped")):
            data, ok, backend = generate_ai_pr(ctx, backend="antigravity")
            assert ok is False
            assert backend == "heuristic"
            assert "ledger" in data["title"]


class TestCliArgsParsing:
    def test_default_args(self):
        args = parse_args([])
        assert args.draft is True
        assert args.dry_run is False
        assert args.yes is False
        assert args.backend == "auto"
        assert args.timeout == 30
        assert args.no_push is False

    def test_flag_overrides(self):
        args = parse_args(["--no-draft", "--dry-run", "-y", "--backend", "codex", "--issue", "12", "--no-push"])
        assert args.draft is False
        assert args.dry_run is True
        assert args.yes is True
        assert args.backend == "codex"
        assert args.issue == "12"
        assert args.no_push is True


class TestMainExecutionFlow:
    @patch("smart_pr.find_gh_cli", return_value=None)
    def test_main_missing_gh(self, mock_gh):
        ret = main(["--dry-run"])
        assert ret == 1

    @patch("smart_pr.find_gh_cli", return_value="C:\\fake\\gh.exe")
    @patch("smart_pr.check_gh_auth", return_value=False)
    def test_main_unauthenticated_gh(self, mock_auth, mock_gh):
        ret = main(["--dry-run"])
        assert ret == 1

    @patch("smart_pr.find_gh_cli", return_value="C:\\fake\\gh.exe")
    @patch("smart_pr.check_gh_auth", return_value=True)
    @patch("smart_pr.get_current_branch", return_value="master")
    @patch("smart_pr.detect_default_branch", return_value="master")
    def test_main_on_default_branch(self, mock_def, mock_curr, mock_auth, mock_gh):
        ret = main(["--dry-run"])
        assert ret == 0

    @patch("smart_pr.find_gh_cli", return_value="C:\\fake\\gh.exe")
    @patch("smart_pr.check_gh_auth", return_value=True)
    @patch("smart_pr.get_current_branch", return_value="feat-branch")
    @patch("smart_pr.detect_default_branch", return_value="master")
    @patch("smart_pr.check_uncommitted_changes", return_value=False)
    def test_main_no_commits_ahead(self, mock_unc, mock_def, mock_curr, mock_auth, mock_gh):
        empty_ctx = PRContext(
            branch="feat-branch",
            base="master",
            base_ref="origin/master",
            commits_ahead=[],
            commits_count=0,
            diff_stat="",
            diff_text="",
            changed_files=[],
            scopes=[],
        )
        with patch("smart_pr.gather_pr_context", return_value=empty_ctx):
            ret = main(["--dry-run"])
            assert ret == 0

    @patch("smart_pr.find_gh_cli", return_value="C:\\fake\\gh.exe")
    @patch("smart_pr.check_gh_auth", return_value=True)
    @patch("smart_pr.get_current_branch", return_value="feat-branch")
    @patch("smart_pr.detect_default_branch", return_value="master")
    @patch("smart_pr.check_uncommitted_changes", return_value=False)
    def test_main_dry_run_success(self, mock_unc, mock_def, mock_curr, mock_auth, mock_gh):
        ctx = PRContext(
            branch="feat-branch",
            base="master",
            base_ref="origin/master",
            commits_ahead=["abc1234 feat(billing): retry"],
            commits_count=1,
            diff_stat="diff stat",
            diff_text="diff text",
            changed_files=[ChangedFileInfo("services/billing/main.py", "billing", "service")],
            scopes=["billing"],
        )
        with patch("smart_pr.gather_pr_context", return_value=ctx):
            ret = main(["--dry-run", "--backend", "heuristic"])
            assert ret == 0

    @patch("smart_pr.find_gh_cli", return_value="C:\\fake\\gh.exe")
    @patch("smart_pr.check_gh_auth", return_value=True)
    @patch("smart_pr.get_current_branch", return_value="feat-branch")
    @patch("smart_pr.detect_default_branch", return_value="master")
    @patch("smart_pr.check_uncommitted_changes", return_value=False)
    def test_main_dry_run_json(self, mock_unc, mock_def, mock_curr, mock_auth, mock_gh, capsys):
        ctx = PRContext(
            branch="feat-branch",
            base="master",
            base_ref="origin/master",
            commits_ahead=["abc1234 feat(billing): retry"],
            commits_count=1,
            diff_stat="diff stat",
            diff_text="diff text",
            changed_files=[ChangedFileInfo("services/billing/main.py", "billing", "service")],
            scopes=["billing"],
        )
        with patch("smart_pr.gather_pr_context", return_value=ctx):
            ret = main(["--dry-run", "--json", "--backend", "heuristic"])
            assert ret == 0
            captured = capsys.readouterr()
            data = json.loads(captured.out)
            assert data["branch"] == "feat-branch"
            assert data["draft"] is True
            assert "feat(billing)" in data["title"]
