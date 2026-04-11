# Login Page Parallel Execution Plan

## Agent profile
- **Agent name:** `auth-core-agent`
- **Worktree suggestion:** `.claude/worktrees/auth-core`
- **Commit priority:** **P1 (must merge first)**

## Goal
Integrate `apps/web/app/login/page.tsx` with Identity login API via Gateway and establish the shared auth/API foundation used by all other frontend agents.

## Service endpoints
- `POST /api/v1/auth/login`
- Optional validation: `GET /api/v1/auth/me`

## Exclusive write set (only this agent edits)
- `apps/web/app/login/page.tsx`
- `apps/web/app/login/page.test.tsx`
- `apps/web/middleware.ts`
- `apps/web/app/page.tsx`
- `apps/web/app/_components/logout-button.tsx`
- `apps/web/app/_lib/api/client.ts`
- `apps/web/app/_lib/api/errors.ts`
- `apps/web/app/_lib/api/types.ts`
- `apps/web/app/_lib/api/auth-login.ts`
- `apps/web/app/_lib/auth/session.ts`
- `apps/web/app/_lib/auth/cookies.ts`

## Forbidden files (to avoid merge conflicts)
- `apps/web/app/signup/**`
- `apps/web/app/billing/**`
- `apps/web/app/history/**`
- `apps/web/app/calculator/focused/**`
- `services/api-gateway/**`

## Contract exported to other agents
Provide stable helpers (no breaking renames after merge):
- `apps/web/app/_lib/api/client.ts`: gateway JSON client
- `apps/web/app/_lib/api/errors.ts`: normalized gateway error parsing
- `apps/web/app/_lib/auth/session.ts`: set/get/clear auth token
- `apps/web/app/_lib/auth/cookies.ts`: auth cookie helpers for middleware compatibility

Other agents must consume these as **read-only**.

## Data contract mapping
Login request:
```json
{
  "email": "user@example.com",
  "password": "minimum_8_characters"
}
```
Login response:
```json
{
  "access_token": "jwt",
  "token_type": "bearer",
  "expires_in": 3600
}
```
Gateway error envelope:
```json
{
  "error": { "code": "...", "message": "..." },
  "request_id": "uuid"
}
```

## Implementation steps
1. Build shared API/auth foundation files in `_lib` (exclusive set above).
2. Replace mock login flow with `auth-login` API call.
3. Persist auth session on success; keep `resolvePostAuthRedirect` behavior.
4. Update middleware/home/logout to rely on real auth session state.
5. Update login tests for API success/failure and validation behavior.

## Commit sequence (inside this plan)
1. **P1.1**: Add shared API/auth foundation files.
2. **P1.2**: Wire login page + login tests.
3. **P1.3**: Wire middleware/home/logout + related tests.

## Merge gate
- This plan merges before all other frontend plans.
- If other agents started from older base, they must rebase/cherry-pick P1 before final merge.
