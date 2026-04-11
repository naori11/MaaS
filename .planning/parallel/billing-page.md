# Billing Page Parallel Execution Plan

## Agent profile
- **Agent name:** `billing-agent`
- **Worktree suggestion:** `.claude/worktrees/billing`
- **Commit priority:** **P4 (merge after P1, can develop in parallel)**

## Goal
Replace billing mocks in `apps/web/app/billing/page.tsx` with Billing service integration through Gateway.

## Service endpoints
- `GET /api/v1/billing/status`
- `POST /api/v1/billing/subscribe`

## Exclusive write set (only this agent edits)
- `apps/web/app/billing/page.tsx`
- `apps/web/app/billing/page.test.tsx`
- `apps/web/app/_lib/api/billing.ts`
- `apps/web/app/_lib/billing/plan-mapper.ts`

## Read-only dependencies (owned by P1)
- `apps/web/app/_lib/api/client.ts`
- `apps/web/app/_lib/api/errors.ts`
- `apps/web/app/_lib/auth/session.ts`

## Forbidden files (to avoid merge conflicts)
- `apps/web/app/login/**`
- `apps/web/app/signup/**`
- `apps/web/app/calculator/focused/**`
- `apps/web/app/history/**`
- `apps/web/middleware.ts`
- `apps/web/app/page.tsx`
- `services/api-gateway/**`

## Plan mapping (locked)
- UI `Hobby` -> backend `Free`
- UI `Pro` -> backend `Standard`
- UI `Enterprise` -> backend `Premium`

## Data contract mapping
Status response:
```json
{
  "plan_name": "Free | Standard | Premium",
  "status": "active | pending_payment",
  "expires_at": "ISO8601 | null"
}
```
Subscribe request:
```json
{
  "plan_name": "Standard | Premium"
}
```
Subscribe response:
```json
{
  "invoice_url": "https://..."
}
```

## Implementation steps
1. Add plan mapper constants/functions.
2. Add `api/billing.ts` using shared client.
3. Replace `mock-billing` load/save path in billing page.
4. Wire subscribe flow with mapped plan names and invoice handling.
5. Update billing tests for API-based behavior.

## Commit sequence (inside this plan)
1. **P4.1**: Add plan mapper + billing API helper.
2. **P4.2**: Wire page behavior + status loading.
3. **P4.3**: Add/adjust tests.

## Merge gate
- Must rebase onto P1 before merge.
- Keep payment method section local-only unless explicitly expanded later.
