# MaaS Workflow & Automation Guide

Comprehensive guide to development, pre-commit validation, code review gates, and automated commit workflows in the **MaaS** monorepo.

---

## Table of Contents

1. [Workflow Architecture Overview](#1-workflow-architecture-overview)
2. [Smart Commit System](#2-smart-commit-system)
   - [Monorepo Scope Clustering](#monorepo-scope-clustering)
   - [Selective File Staging](#selective-file-staging)
   - [Skipping or Selecting Groups](#skipping-or-selecting-groups)
   - [Commit Message Synthesis](#commit-message-synthesis)
3. [Pre-commit Review Gates (Lefthook)](#3-pre-commit-review-gates-lefthook)
   - [Gate 1: Deterministic QA Check (Hard Blocker)](#gate-1-deterministic-qa-check-hard-blocker)
   - [Gate 2: AI Security Review (Advisory)](#gate-2-ai-security-review-advisory)
   - [Gate 3: AI Hallucination & Scope Review (Advisory)](#gate-3-ai-hallucination--scope-review-advisory)
   - [Gate 4: Conventional Commitlint (`commit-msg`)](#gate-4-conventional-commitlint-commit-msg)
4. [AI Backend Abstraction](#4-ai-backend-abstraction)
5. [AI Agent Integration & The Iron Laws](#5-ai-agent-integration--the-iron-laws)
6. [Commands Quick Reference](#6-commands-quick-reference)

---

## 1. Workflow Architecture Overview

The repository enforces clean code, atomic commits, security scanning, and conventional git history through a layered automation pipeline:

```mermaid
flowchart TD
    subgraph Development ["1. Development Phase"]
        Edit["Developer / Agent modifies code"]
        Impact["GitNexus impact() analysis"]
    end

    subgraph Staging ["2. Smart Commit Staging"]
        Trigger["pnpm commit / python scripts/smart_commit.py"]
        Select{"File / Scope Filter?"}
        Filter["Positional paths / --pick / --scope / --staged-only"]
        Cluster["Semantic Monorepo Clusterer\n(groups apps, services, tests, docs)"]
        SkipFilter["Group Selector / Skipper\n(skips excluded groups)"]
        MsgGen["Conventional Message Synthesis\n(AI with deterministic fallback)"]
        Preview["Summary Table & Visual Cards"]
        Approval{"Manual Approval"}
    end

    subgraph Gates ["3. Lefthook Pre-commit Gates"]
        QA["Gate 1: QA Check\n(ruff lint, debug artifacts, conflict markers)\n⛔ HARD BLOCKER"]
        Sec["Gate 2: AI Security Review\n(secrets, injection, SSRF, permissive CORS)\n⚠️ ADVISORY"]
        Halluc["Gate 3: AI Hallucination Review\n(scope checks vs .planning/ specs)\n⚠️ ADVISORY"]
        MsgLint["Gate 4: commitlint (commit-msg)\n(Conventional Commits ≤72-char header)\n⛔ HARD BLOCKER"]
        Report[".precommit-review.json Report"]
    end

    Edit --> Trigger
    Trigger --> Select
    Select -->|Yes| Filter --> Cluster
    Select -->|No (All)| Cluster
    Cluster --> SkipFilter --> MsgGen --> Preview --> Approval
    Approval -->|Approved| Subprocess["git add <group_files>\ngit commit -m <msg>"]
    Approval -->|Aborted| Abort["No changes committed"]
    Subprocess --> Gates
    QA --> Sec --> Halluc --> MsgLint --> Report --> GitHistory["✅ Atomic Git Commit"]
```

---

## 2. Smart Commit System

Entrypoint: [`scripts/smart_commit.py`](file:///C:/Projects/MaaS/scripts/smart_commit.py)

CLI agents and developers frequently work across multiple services in a monorepo. Running raw `git add .` creates monolithic, unstructured commits that are difficult to review and bisect. Smart Commit solves this by:
1. Scanning `git status` while filtering out runtime noise (caches, `.obsidian`, `.smart-env`, `.precommit-review.json*`).
2. Clustering files into atomic groups by monorepo domain and coupling unit tests with their source code.
3. Synthesizing valid Conventional Commit messages.
4. Executing `git add` and `git commit` via safe Python `subprocess` lists (eliminating Windows PowerShell string escaping bugs).

### Monorepo Scope Clustering

| File Pattern | Scope | Category | Notes |
|---|---|---|---|
| `apps/web/**` | `web` | `app` | Unit tests (`*.test.tsx`) are clustered into the `web` group |
| `services/api-gateway/**` | `gateway` | `service` | Paired with gateway unit tests |
| `services/billing/**` | `billing` | `service` | Paired with billing unit tests |
| `services/ledger/**` | `ledger` | `service` | Paired with ledger unit tests |
| `services/identity/**` | `identity` | `service` | Paired with identity unit tests |
| `services/math-<op>/**` | `math-<op>` | `service` | E.g. `math-add`, `math-subtract`, `math-multiply`, `math-divide` |
| `services/nginx/**` | `nginx` | `infra` | NGINX reverse proxy configuration |
| `scripts/precommit/**` | `precommit` | `chore` / `test` | Pre-commit scripts and test suite |
| `scripts/**` | `chore` | `chore` | General tooling and utility scripts |
| `.github/**` | `ci` | `infra` | GitHub Actions CI/CD workflows and deployment scripts |
| `infra/**`, `docker-compose*`, `Dockerfile*`, `*.tf` | `docker` / `ci` | `infra` | Infrastructure and container manifests |
| `docs/**`, `.planning/**`, `*.md` | *(none / root)* | `docs` | Documentation and planning specifications |
| `package.json`, `turbo.json`, `pnpm-workspace.yaml` | `build` | `build` | Monorepo and workspace build configs |
| `pnpm-lock.yaml` | `deps` | `build` | Dependency lockfile adjustments |

### Selective File Staging

When you have a working tree with many modified files and only want to commit specific ones:

- **Specific paths / folders**:
  ```bash
  pnpm commit apps/web/
  pnpm commit package.json scripts/smart_commit.py
  ```
- **Interactive File Picker (`--pick` / `pnpm commit:pick`)**:
  Presents a numbered checklist of all changed files to select from:
  ```bash
  pnpm commit:pick
  ```
  ```text
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ 📋 SELECT FILES TO COMMIT (42 changed files available)                      │
  └─────────────────────────────────────────────────────────────────────────────┘
    [ 1] [MODIFIED] (general)           README.md
    [ 2] [MODIFIED] (build)             package.json
    [ 3] [MODIFIED] (deps)              pnpm-lock.yaml
    [ 4] [NEW]      (chore)             scripts/smart_commit.py

  Select file numbers to commit (e.g. '1, 4' or '1-3') [all]: 2, 4
  ```
- **Scope Filter (`--scope <name>`)**:
  ```bash
  python scripts/smart_commit.py --scope billing
  ```
- **Staged-Only (`--staged-only` / `pnpm commit:staged`)**:
  Only commits files you have explicitly added via `git add <files>`.

### Skipping or Selecting Groups

When multiple commit groups are recommended, you can selectively apply or skip groups:

- **At the interactive prompt**:
  ```text
  Select action [all]: skip 1
  ```
  - `all` or `Enter`: Commits all recommended groups.
  - `skip 1` or `-1`: Skips Group 1 and commits the rest.
  - `2, 4`: Commits only Groups 2 and 4.
  - `i`: Enters step-by-step confirmation (`[Y/n/edit]`).
  - `q`: Aborts without committing anything.
- **Via CLI flags**:
  ```bash
  python scripts/smart_commit.py --skip-groups 1
  python scripts/smart_commit.py --groups 2,4
  ```

### Commit Message Synthesis

The generator strictly adheres to the repository's [`commitlint.config.js`](file:///C:/Projects/MaaS/commitlint.config.js) and [`CONTRIBUTING.md`](file:///C:/Projects/MaaS/CONTRIBUTING.md):
- **Format**: `<type>(<scope>): <subject>`
- **Types**: `feat`, `fix`, `docs`, `build`, `refactor`, `chore`, `ci`, `test`, `revert`, `perf`.
- **Header Max Length**: 72 characters.
- **Subject Style**: Lowercase first word, imperative mood (`add`, not `added`), no trailing period.
- **Body Style**: Wrapped at 100 characters per line explaining WHAT changed and WHY.

---

## 3. Pre-commit Review Gates (Lefthook)

Configuration: [`lefthook.yml`](file:///C:/Projects/MaaS/lefthook.yml)  
Documentation: [`scripts/precommit/README.md`](file:///C:/Projects/MaaS/scripts/precommit/README.md)

Lefthook manages active git hooks located in `.git/hooks/`. On every commit attempt, it executes deterministic QA checks, AI security scanners, scope validation, and commitlint.

```
git commit
  ├── pre-commit
  │     ├── 1. qa-check (qa_check.py)           ⛔ Hard Blocker
  │     ├── 2. security-review (security_review.py) ⚠️ Advisory
  │     └── 3. hallucination-review (hallucination_review.py) ⚠️ Advisory
  └── commit-msg
        └── 4. commitlint                       ⛔ Hard Blocker
```

### Gate 1: Deterministic QA Check (Hard Blocker)
- **Script**: `scripts/precommit/qa_check.py` (and `qa_check.sh`)
- **What it checks**:
  1. **Python linting**: Executes Ruff (`ruff check`) against staged `.py` files.
  2. **Debug artifacts**: Scans for `console.log`, `debugger`, and `print()` in service production code.
  3. **Unresolved conflict markers**: Flags `<<<<<<<`, `=======`, `>>>>>>>`.
  4. **Test co-location**: Verifies that backend services place tests under `tests/`.
- **Enforcement**: **Hard blocker**. Commits are rejected if any check fails.

### Gate 2: AI Security Review (Advisory)
- **Script**: `scripts/precommit/security_review.py`
- **What it checks**:
  - Scans diffs for exposed API keys, credentials, SQL injection, command injection, SSRF, overly permissive CORS (`*`), path traversal, and auth/authz bypasses.
- **Enforcement**: Warn-only by default. Writes findings to `.precommit-review.json`.

### Gate 3: AI Hallucination & Scope Review (Advisory)
- **Script**: `scripts/precommit/hallucination_review.py`
- **What it checks**:
  - Matches staged file diffs against architectural plans under `.planning/`.
  - Flags unapproved routes, contract mismatches, goal divergence, or forbidden file edits.
- **Enforcement**: Warn-only by default. Writes findings to `.precommit-review.json`.

### Gate 4: Conventional Commitlint (`commit-msg`)
- **Tool**: `@commitlint/cli` + `@commitlint/config-conventional`
- **Configuration**: [`commitlint.config.js`](file:///C:/Projects/MaaS/commitlint.config.js)
- **Enforcement**: **Hard blocker**. Rejects commit messages that violate Conventional Commits formatting or length constraints.

### Machine-Readable Report (`.precommit-review.json`)
After every commit attempt, Lefthook generates `.precommit-review.json`. AI coding agents inspect this file to verify hook results:
```json
{
  "timestamp": "2026-11-11T10:00:00Z",
  "overall_status": "pass",
  "checks": {
    "qa_check": { "status": "pass", "blocker": true },
    "security_review": { "status": "pass", "blocker": false, "findings": [] },
    "hallucination_review": { "status": "pass", "blocker": false, "findings": [] }
  }
}
```

---

## 4. AI Backend Abstraction

Module: [`scripts/precommit/ai_backend.py`](file:///C:/Projects/MaaS/scripts/precommit/ai_backend.py)

All AI-powered tasks (commit message generation, security scanning, hallucination detection) use a unified multi-backend abstraction with automatic fallback:

1. **Antigravity CLI (`agy`)**: Powered by Gemini; best quality for complex reasoning.
2. **Codex CLI (`codex`)**: Powered by OpenAI; fast non-interactive execution (3–5s).
3. **Ollama Local API (`qwen2.5:7b`)**: Offline fallback on `http://127.0.0.1:11434`.
4. **Deterministic Heuristics**: Fallback for instant generation without any AI calls.

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PRECOMMIT_AI_BACKEND` | `auto` | Force backend: `auto`, `antigravity`, `codex`, `ollama`, or `heuristic`. |
| `PRECOMMIT_TIMEOUT` | `20` | Timeout in seconds for AI backend calls. |
| `PRECOMMIT_AI_STRICT` | `0` | Set to `1` to block commits on advisory AI findings. |
| `PRECOMMIT_MODEL` | `qwen2.5:7b` | Model name for Ollama backend. |
| `OLLAMA_HOST` | `127.0.0.1` | Hostname for local Ollama server. |
| `OLLAMA_PORT` | `11434` | Port for local Ollama server. |
| `PLANNING_DIR` | `.planning` | Directory containing planning specifications for hallucination review. |
| `PRECOMMIT_DEBUG` | `0` | Set to `1` to display detailed backend subprocess logs and exit codes. |

---

## 5. AI Agent Integration & The Iron Laws

Documented in [`AGENTS.md`](file:///C:/Projects/MaaS/AGENTS.md) and [`.agents/skills/smart-commit/SKILL.md`](file:///C:/Projects/MaaS/.agents/skills/smart-commit/SKILL.md).

When AI CLI agents (Antigravity, Codex, Claude Code) operate in this repository, they must strictly follow **The Two Iron Laws**:

> [!IMPORTANT]
> ### The Two Iron Laws of Commits
> 
> 1. **No Raw Shell Git Commits**:
>    CLI agents must **NEVER** run raw `git add` or `git commit` commands directly. All commits must be executed through `python scripts/smart_commit.py`.
> 
> 2. **Manual Approval Protocol**:
>    Commits are **ALWAYS** subject to manual user approval.
>    - Step 1: Agent runs `python scripts/smart_commit.py --dry-run`.
>    - Step 2: Agent presents proposed groups, file lists, and commit messages in chat.
>    - Step 3: Agent **waits for user approval**.
>    - Step 4: Only after user confirmation, agent executes `python scripts/smart_commit.py --yes`.

---

## 6. Commands Quick Reference

### Smart Commit Commands

| Task | Command |
|---|---|
| **Interactive Commit (Default)** | `pnpm commit`<br>`python scripts/smart_commit.py` |
| **Interactive File Picker** | `pnpm commit:pick`<br>`python scripts/smart_commit.py --pick` |
| **Commit Only Staged Files** | `pnpm commit:staged`<br>`python scripts/smart_commit.py --staged-only` |
| **Commit Specific Files / Folders** | `pnpm commit apps/web/`<br>`python scripts/smart_commit.py package.json scripts/smart_commit.py` |
| **Filter by Monorepo Scope** | `python scripts/smart_commit.py --scope billing` |
| **Skip Specific Recommended Groups** | `python scripts/smart_commit.py --skip-groups 1`<br>*(or type `skip 1` at the interactive prompt)* |
| **Commit Only Specific Groups** | `python scripts/smart_commit.py --groups 2,4`<br>*(or type `2, 4` at the interactive prompt)* |
| **Preview Only (Dry Run)** | `pnpm commit:dry`<br>`python scripts/smart_commit.py --dry-run` |
| **Dry Run with Full File Lists** | `python scripts/smart_commit.py --dry-run -v` |
| **Fast Offline Commit (<1s)** | `pnpm commit:fast`<br>`python scripts/smart_commit.py --backend heuristic` |
| **Fast Codex Commit (3–5s)** | `pnpm commit:codex`<br>`python scripts/smart_commit.py --backend codex` |
| **Non-Interactive Execution** | `pnpm commit:auto`<br>`python scripts/smart_commit.py --yes` |

### Pre-commit Hook & Quality Commands

| Task | Command |
|---|---|
| **Run Deterministic QA Check** | `python scripts/precommit/qa_check.py [files...]`<br>`bash scripts/precommit/qa_check.sh [files...]` |
| **Run Security Scanner Manually** | `python scripts/precommit/security_review.py [files...]` |
| **Run Hallucination Scanner Manually** | `python scripts/precommit/hallucination_review.py [files...]` |
| **Run All Lefthook Pre-commit Hooks** | `npx lefthook run pre-commit` |
| **Run Commit-msg Lint Hook** | `npx lefthook run commit-msg` |
| **Test Smart Commit Test Suite** | `pytest scripts/precommit/test_smart_commit.py -v` |
| **Bypass Hooks (Use Sparingly)** | `git commit --no-verify -m "..."` |
| **Exclude a Specific Hook** | `LEFTHOOK_EXCLUDE=hallucination-review git commit -m "..."` |

### Monorepo & Dev Commands

| Task | Command |
|---|---|
| **Install Dependencies & Hooks** | `pnpm install` |
| **Run All Services & Web Dev** | `pnpm dev` |
| **Build Entire Monorepo** | `pnpm build` |
| **Lint All Services & Apps** | `pnpm lint` |
| **Run All Workspace Tests** | `pnpm test` |
| **Run Specific Service Tests** | `pnpm --filter billing test`<br>`cd services/billing && pytest` |
| **Start Local Docker Cluster** | `docker compose up -d --build` |
| **Check Docker Services** | `docker compose ps` |
| **Stop Local Docker Cluster** | `docker compose down` |

### GitNexus Code Intelligence Commands

| Task | Command / Tool |
|---|---|
| **Check Knowledge Graph Status** | `node .gitnexus/run.cjs status` |
| **Re-index / Analyze Repository** | `node .gitnexus/run.cjs analyze` |
| **Symbol Impact Analysis** | `impact({target: "symbolName", direction: "upstream"})` |
| **Verify Pre-commit Scope** | `detect_changes({scope: "compare", base_ref: "master"})` |
