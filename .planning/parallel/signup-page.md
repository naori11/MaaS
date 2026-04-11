# Signup Page Parallel Execution Plan

## Agent profile
- **Agent name:** `signup-agent`
- **Worktree suggestion:** `.claude/worktrees/signup`
- **Commit priority:** **P2 (merge after P1)**

## Goal
Integrate `apps/web/app/signup/page.tsx` with Identity register API via Gateway, while keeping Full Name as optional UI-only.

## Service endpoints
- `POST /api/v1/auth/register`
- Optional post-register flow: `POST /api/v1/auth/login` (only if required by auth policy from P1)

## Exclusive write set (only this agent edits)
- `apps/web/app/signup/page.tsx`
- `apps/web/app/signup/page.test.tsx`
- `apps/web/app/_lib/api/auth-register.ts`

## Read-only dependencies (owned by P1)
- `apps/web/app/_lib/api/client.ts`
- `apps/web/app/_lib/api/errors.ts`
- `apps/web/app/_lib/auth/session.ts`
- `apps/web/app/_lib/auth/cookies.ts`

## Forbidden files (to avoid merge conflicts)
- `apps/web/app/login/**`
- `apps/web/middleware.ts`
- `apps/web/app/page.tsx`
- `apps/web/app/_components/logout-button.tsx`
- `apps/web/app/billing/**`
- `apps/web/app/history/**`
- `apps/web/app/calculator/focused/**`
- `services/api-gateway/**`

## Field policy (locked)
- Keep **Full Name** visible in UI.
- Make Full Name optional/non-blocking.
- Do not send Full Name to backend payload.

## Data contract mapping
Register request:
```json
{
  "email": "user@example.com",
  "password": "minimum_8_characters"
}
```
Register response:
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "created_at": "ISO8601"
}
```

## Implementation steps
1. Add `auth-register.ts` using shared `api/client`.
2. Update signup submit handler to call register endpoint.
3. Keep redirect sanitation via existing `resolvePostAuthRedirect`.
4. Set session via P1 auth session helpers.
5. Update tests (validation + success + API failure).

## Commit sequence (inside this plan)
1. **P2.1**: Add register API helper and wire submit flow.
2. **P2.2**: Adjust validation (name optional) and update tests.

## Merge gate
- Rebase onto P1 before merge.
- Do not edit P1-owned files to resolve conflicts; if needed, coordinate with `auth-core-agent`.
