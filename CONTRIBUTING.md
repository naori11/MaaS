# Contributing to MaaS

This guide covers the commit, branch, and pull request conventions used in this repository.

## Commit Messages

We follow [Conventional Commits v1.0.0](https://www.conventionalcommits.org/en/v1.0.0/). Every commit message must match this format:

```
<type>(<scope>): <subject>

[optional body]

[optional footer(s)]
```

Commits are validated automatically by **commitlint** via a Lefthook `commit-msg` hook.

### Types

| Type       | When to use                                              |
| ---------- | -------------------------------------------------------- |
| `feat`     | New feature or capability                                |
| `fix`      | Bug fix                                                  |
| `docs`     | Documentation only                                       |
| `build`    | Build system, dependencies, or infrastructure            |
| `refactor` | Code change that neither fixes a bug nor adds a feature  |
| `chore`    | Maintenance tasks (configs, tooling, no production code) |
| `ci`       | CI/CD pipeline changes                                   |
| `test`     | Adding or updating tests                                 |
| `revert`   | Reverting a previous commit                              |
| `perf`     | Performance improvement                                  |

### Scopes

Scope is optional but recommended for `feat`, `fix`, `refactor`, and `test` commits.

| Scope       | Maps to                                       |
| ----------- | --------------------------------------------- |
| `web`       | `apps/web`                                    |
| `gateway`   | `services/api-gateway`                        |
| `billing`   | `services/billing`                            |
| `ledger`    | `services/ledger`                             |
| `identity`  | `services/identity`                           |
| `math-*`    | `services/math-add`, `math-subtract`, etc.    |
| `nginx`     | NGINX reverse proxy configuration             |
| `deps`      | Production dependency updates                 |
| `deps-dev`  | Dev dependency updates                        |
| `ci`        | `.github/workflows`, CI scripts               |
| `docker`    | `docker-compose.yml`, Dockerfiles             |
| `precommit` | Pre-commit hooks, Lefthook configuration      |

### Subject Line Rules

1. **Imperative mood** — "add checkout flow" not "added checkout flow"
2. **Lowercase first word** — `feat(web): add checkout` not `feat(web): Add checkout`
3. **No trailing period**
4. **Max 72 characters** for the entire first line (type + scope + colon + subject)
5. **Breaking changes** — append `!` before the colon: `feat(gateway)!: remove v1 auth endpoint`

### Body (optional, encouraged for `feat` and `fix`)

- Separate from the subject with a blank line
- Wrap at 100 characters per line
- Explain **what** changed and **why**, not how

### Footers

- `BREAKING CHANGE: <description>` for breaking changes
- `Closes #<issue>` or `Fixes #<issue>` to auto-close GitHub issues

### Examples

```
feat(billing): add webhook retry with exponential backoff

Xendit webhooks occasionally fail on first delivery. This adds a retry
queue with exponential backoff (max 3 attempts, 30s/60s/120s delays)
to prevent missed payment notifications.

Closes #102
```

```
fix(web): prevent double-submit on checkout button
```

```
docs: add ngrok setup guide for local subscription testing
```

---

## Branch Naming

Use a type prefix followed by a kebab-case description:

```
<type>/<kebab-case-description>
```

| Prefix      | When to use          | Example                        |
| ----------- | -------------------- | ------------------------------ |
| `feat/`     | New feature work     | `feat/subscription-flow`       |
| `fix/`      | Bug fixes            | `fix/jwt-timestamp-mismatch`   |
| `docs/`     | Documentation only   | `docs/ngrok-setup-guide`       |
| `chore/`    | Maintenance, deps    | `chore/dependency-updates`     |
| `refactor/` | Code restructuring   | `refactor/history-table-layout`|
| `ci/`       | CI/CD changes        | `ci/oidc-deployment`           |
| `test/`     | Test additions       | `test/ledger-persistence`      |

---

## Pull Requests

### PR Title

PR titles follow the same Conventional Commits format as commit subjects:

```
<type>(<scope>): <subject>
```

Multiple scopes are allowed (comma-separated) since PRs often span services:

```
feat(billing,web): add subscription checkout and Pro plan management
```

### PR Description

A template auto-populates when you open a PR. Fill in every section:

1. **What does this PR do?** — List each feature/change with a plain-English explanation. Imagine you are telling a non-technical teammate what changed.
2. **Technical Details** — Explain the implementation for code reviewers, grouped by service/component.
3. **Breaking Changes** — Delete this section if none; otherwise list what breaks and what consumers must do.
4. **How to Test** — Exact steps to verify (commands, UI flows, curl examples).
5. **Related Issues** — Link issues with `Closes #N`.
6. **Screenshots / Recordings** — Required for any `apps/web` UI changes.

See [`.github/pull_request_template.md`](.github/pull_request_template.md) for the full template.

---

## Tooling

| Tool | Purpose | Config |
| --- | --- | --- |
| [commitlint](https://commitlint.js.org/) | Validates commit messages on every commit | `commitlint.config.js` |
| [Lefthook](https://github.com/evilmartians/lefthook) | Runs git hooks (commit-msg + pre-commit) | `lefthook.yml` |
| [Smart Commit](docs/WORKFLOW_AUTOMATIONS.md) | Automatic monorepo grouping and conventional commits | `scripts/smart_commit.py` |

### Workflow Automations & Guide

For comprehensive documentation on pre-commit review gates, AI security/hallucination scanners, and smart commit options, see:
👉 [**Workflow & Automation Guide**](docs/WORKFLOW_AUTOMATIONS.md)

Quick commit shortcuts:
- `pnpm commit`: Standard interactive commit with atomic scope clustering
- `pnpm commit:pick`: Interactive file picker
- `pnpm commit:dry`: Preview proposed commit groups and messages
- `pnpm commit:staged`: Commit only files already staged with `git add`
- `pnpm commit:codex`: Fast commit message generation using Codex CLI
- `pnpm commit:fast`: Instant offline commit using deterministic rules
- `pnpm commit:auto`: Non-interactive execution (for agents after approval)

### Setup

After cloning, install dependencies and Lefthook will activate automatically:

```bash
pnpm install
```

### Bypassing hooks (use sparingly)

```bash
git commit --no-verify -m "WIP: temporary work-in-progress"
```

> **Note:** CI will still enforce lint and test checks regardless of local hook bypasses.
