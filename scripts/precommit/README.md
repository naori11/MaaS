# Local AI Pre-commit Code Reviewer

A local pre-commit review gate built on **Lefthook** and AI backends. It runs three parallel checks before every commit:

1. **QA Check (`qa_check.sh` / `qa_check.py`)**: Deterministic quality checks (ruff python linting, debug artifacts like `console.log`/`debugger`, unresolved git conflict markers, `print()` in service code, test co-location). **Hard blocker**.
2. **Security Review (`security_review.py`)**: AI-powered security scanner checking diffs for secrets, injection, SSRF, permissive CORS, path traversal, auth/authz issues, etc. Warn-only by default.
3. **Hallucination Review (`hallucination_review.py`)**: AI-powered scope & contract checker comparing staged diffs against `.planning/` specifications (detects unapproved routes, contract mismatches, forbidden file edits, goal divergence). Warn-only by default.

---

## AI Backend Priority Order

The AI checks use an automatic fallback strategy:

1. **Primary: Antigravity CLI (`agy --print`)** — Powered by Gemini, highest quality, non-interactive JSON mode.
2. **Fallback: Codex CLI (`codex exec`)** — Powered by OpenAI, used when Antigravity is unavailable or fails.
3. **Tertiary: Ollama local API (`qwen2.5:7b`)** — Offline fallback on `http://127.0.0.1:11434`.

If no AI backend is available, AI checks skip gracefully with an advisory warning (exit 0). The deterministic QA check always runs regardless.

---

## Configuration & Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PRECOMMIT_AI_BACKEND` | `auto` | Force backend: `auto`, `antigravity`, `codex`, or `ollama`. |
| `PRECOMMIT_AI_STRICT` | `0` | Set to `1` to block commits on AI findings in interactive mode. |
| `PRECOMMIT_TIMEOUT` | `90` | Timeout in seconds for AI backend calls. |
| `PRECOMMIT_MODEL` | `qwen2.5:7b` | Model name for Ollama backend. |
| `OLLAMA_HOST` | `127.0.0.1` | Hostname for Ollama server. |
| `OLLAMA_PORT` | `11434` | Port for Ollama server. |
| `PLANNING_DIR` | `.planning` | Directory containing planning specifications. |

---

## Dual-Mode Output

- **Interactive Terminal**: Formatted text with ANSI colors and status indicators (`✅`, `⚠`, `✗`, `ℹ`).
- **Machine-Readable Report (`.precommit-review.json`)**: Written on every commit attempt. AI agents (such as Antigravity, Claude Code, or Codex) inspect this file to self-correct findings before proceeding.

---

## AI Agent Integration

When AI agents run commits:
- Hooks detect non-interactive / agent environment.
- Advisory AI findings do not hard-block agent execution (preventing infinite commit retry loops).
- Agents read `.precommit-review.json` after committing to resolve any flagged issues.
- The deterministic QA check remains a hard blocker for everyone.

---

## Skip Commands

- Skip all hooks:
  ```bash
  git commit --no-verify
  ```
- Exclude a specific hook:
  ```bash
  LEFTHOOK_EXCLUDE=hallucination-review git commit -m "..."
  ```
- Run checks manually:
  ```bash
  bash scripts/precommit/qa_check.sh
  python scripts/precommit/security_review.py
  python scripts/precommit/hallucination_review.py
  ```
