# Parallel Worktree Orchestrator

This runbook coordinates parallel agent work in separate git worktrees, with sequential merge priority to minimize conflicts.

## Source plans
- `login-page.md` (P1)
- `signup-page.md` (P2)
- `calculator-focused-page.md` (P3)
- `billing-page.md` (P4)
- `history-page.md` (P5.1 then P6.x)

## Canonical merge order
1. **P1** `auth-core-agent` (login + shared auth/api foundation)
2. **P2** `signup-agent`
3. **P3** `calculator-agent`
4. **P4** `billing-agent`
5. **P5.1** `history-ledger-agent` gateway patch
6. **P6.1/P6.2** `history-ledger-agent` history frontend

---

## 1) Create worktrees
From repository root:

```bash
git worktree add .claude/worktrees/auth-core -b feat/p1-auth-core master
git worktree add .claude/worktrees/signup -b feat/p2-signup master
git worktree add .claude/worktrees/calculator -b feat/p3-calculator master
git worktree add .claude/worktrees/billing -b feat/p4-billing master
git worktree add .claude/worktrees/history-ledger -b feat/p5-p6-history-ledger master
```

> If your default base branch differs, replace `master` with your chosen base.

---

## 2) Agent assignment
- Worktree `.claude/worktrees/auth-core` -> execute `login-page.md`
- Worktree `.claude/worktrees/signup` -> execute `signup-page.md`
- Worktree `.claude/worktrees/calculator` -> execute `calculator-focused-page.md`
- Worktree `.claude/worktrees/billing` -> execute `billing-page.md`
- Worktree `.claude/worktrees/history-ledger` -> execute `history-page.md`

Each agent must follow its **Exclusive write set** and **Forbidden files** from its plan.

---

## 3) Per-agent local flow
Inside each assigned worktree:

```bash
git status
# implement only files allowed by that plan
pnpm -C apps/web test
# and/or relevant service tests if gateway touched
git add <explicit-files-only>
git commit -m "<scope>: <summary>"
```

For `history-ledger-agent`:
- Commit gateway patch first (**P5.1**)
- Commit history frontend second (**P6.1/P6.2**)

---

## 4) Sequential integration flow (main worktree)
From main repository working directory:

```bash
git checkout master
git pull
```

### Merge P1
```bash
git merge --no-ff feat/p1-auth-core
```

### Rebase remaining branches onto updated master
```bash
git checkout feat/p2-signup && git rebase master
git checkout feat/p3-calculator && git rebase master
git checkout feat/p4-billing && git rebase master
git checkout feat/p5-p6-history-ledger && git rebase master
```

### Merge P2 -> P4 in order
```bash
git checkout master && git merge --no-ff feat/p2-signup
git checkout master && git merge --no-ff feat/p3-calculator
git checkout master && git merge --no-ff feat/p4-billing
```

### Merge P5.1 first, then P6.x
If P5.1 and P6.x are separate commits on `feat/p5-p6-history-ledger`, either:
1) merge whole branch if already ordered and validated, or
2) cherry-pick gateway commit first, then remaining history commits.

Example cherry-pick flow:
```bash
git checkout master
git cherry-pick <p5_1_gateway_commit_sha>
git cherry-pick <p6_1_commit_sha> <p6_2_commit_sha>
```

---

## 5) Conflict policy
- Do not resolve conflicts by editing files outside each plan’s ownership unless explicitly approved.
- If conflict involves P1-owned shared files (`_lib/api/*`, `_lib/auth/*`), prefer preserving P1 contract and adapting downstream branches.
- Re-run affected tests after each merge step.

---

## 6) Verification checkpoints
After each priority merge:
1. `pnpm -C apps/web test`
2. If gateway changed: run gateway tests
3. Smoke-check pages in order:
   - `/login`, `/signup`
   - `/calculator/focused`
   - `/billing`
   - `/history`

Final checkpoint on `master`:
```bash
git log --oneline --decorate -n 15
git status
```

---

## 7) Optional cleanup
After successful integration:

```bash
git worktree list
# remove completed worktrees as needed
git worktree remove .claude/worktrees/auth-core
git worktree remove .claude/worktrees/signup
git worktree remove .claude/worktrees/calculator
git worktree remove .claude/worktrees/billing
git worktree remove .claude/worktrees/history-ledger
```
