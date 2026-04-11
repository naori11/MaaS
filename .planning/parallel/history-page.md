# History Page Parallel Execution Plan

## Agent profile
- **Agent name:** `history-ledger-agent`
- **Worktree suggestion:** `.claude/worktrees/history-ledger`
- **Commit priority:** **P5 (gateway patch) then P6 (history UI)**

## Goal
Enable ledger history through Gateway, then integrate `apps/web/app/history/page.tsx` with ledger transactions.

## Service endpoints
- `GET /api/v1/ledger/transactions?limit=...`

## Exclusive write set (only this agent edits)
- `services/api-gateway/main.py`
- `services/api-gateway/tests/test_gateway_api.py`
- `apps/web/app/history/page.tsx`
- `apps/web/app/history/page.test.tsx`
- `apps/web/app/_lib/api/ledger.ts`
- `apps/web/app/_lib/history/adapter.ts`

## Read-only dependencies (owned by P1)
- `apps/web/app/_lib/api/client.ts`
- `apps/web/app/_lib/api/errors.ts`
- `apps/web/app/_lib/auth/session.ts`

## Forbidden files (to avoid merge conflicts)
- `apps/web/app/login/**`
- `apps/web/app/signup/**`
- `apps/web/app/calculator/focused/**`
- `apps/web/app/billing/**`
- `apps/web/middleware.ts`
- `apps/web/app/page.tsx`

## Required sequence (non-negotiable)
1. Add Gateway ledger pass-through route + tests.
2. After route is in place, wire history frontend.

## Data contract mapping
Ledger response:
```json
{
  "items": [
    {
      "request_id": "...",
      "operation_type": "addition | subtraction | multiplication | division",
      "operand_a": 10,
      "operand_b": 5,
      "result": 15,
      "math_transaction_id": "...",
      "created_at": "ISO8601"
    }
  ]
}
```
Adapt to UI `HistoryRow` fields:
- id, inputA, operation, inputB, result, timestamp, status, error

## Implementation steps
1. Patch gateway route mapping/handler for ledger GET forwarding.
2. Add gateway tests for auth + forwarding + query param behavior.
3. Add `api/ledger.ts` and history adapter.
4. Replace `loadHistoryRows()` with ledger fetch in history page.
5. Keep filter/pagination/export UI semantics.
6. Update history tests for API-fed data.

## Commit sequence (inside this plan)
1. **P5.1**: Gateway route + gateway tests.
2. **P6.1**: Ledger API helper + adapter.
3. **P6.2**: History page wiring + tests.

## Merge gate
- Rebase onto P1 before frontend merge.
- Recommended merge order: P5.1 first, then P6.x.
