# Calculator Focused Parallel Execution Plan

## Agent profile
- **Agent name:** `calculator-agent`
- **Worktree suggestion:** `.claude/worktrees/calculator`
- **Commit priority:** **P3 (merge after P1, can develop in parallel)**

## Goal
Wire `apps/web/app/calculator/focused/page.tsx` to math services through Gateway and convert static keypad into functional calculator behavior.

## Service endpoints
- `POST /api/v1/calculate/add`
- `POST /api/v1/calculate/subtract`
- `POST /api/v1/calculate/multiply`
- `POST /api/v1/calculate/divide`

## Exclusive write set (only this agent edits)
- `apps/web/app/calculator/focused/page.tsx`
- `apps/web/app/calculator/focused/page.test.tsx`
- `apps/web/app/_lib/api/math.ts`
- `apps/web/app/_lib/calculator/model.ts`

## Read-only dependencies (owned by P1)
- `apps/web/app/_lib/api/client.ts`
- `apps/web/app/_lib/api/errors.ts`
- `apps/web/app/_lib/auth/session.ts`

## Forbidden files (to avoid merge conflicts)
- `apps/web/app/login/**`
- `apps/web/app/signup/**`
- `apps/web/app/billing/**`
- `apps/web/app/history/**`
- `apps/web/middleware.ts`
- `apps/web/app/page.tsx`
- `services/api-gateway/**`

## Data contract mapping
Request payload:
```json
{
  "operand_a": 10,
  "operand_b": 5
}
```
Response payload:
```json
{
  "operation": "addition | subtraction | multiplication | division",
  "result": 15,
  "transaction_id": "...",
  "timestamp": "ISO8601"
}
```

## Implementation steps
1. Add `calculator/model.ts` for calculator state transitions.
2. Add `api/math.ts` endpoint mapping for operators.
3. Wire `=` execution to API call and render result.
4. Handle divide-by-zero and gateway errors in display-safe state.
5. Update calculator tests for interaction and endpoint mapping.

## Commit sequence (inside this plan)
1. **P3.1**: Add math API wrapper + model.
2. **P3.2**: Wire page interactions and result/error rendering.
3. **P3.3**: Add/adjust tests.

## Merge gate
- Must rebase onto P1 before final merge.
- No cross-domain edits allowed.
