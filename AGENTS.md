# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Big picture

MaaS is a pnpm/turbo monorepo built around a public API gateway and a set of private FastAPI services.

- `apps/web`: Next.js frontend using App Router, Tailwind, and framer-motion. Most of the frontend logic lives in route shells, layout/template components, and small API/session helpers under `app/_lib`.
- `services/*`: Python microservices. The gateway is the only public HTTP surface; identity issues JWTs, billing handles Xendit subscription/webhook flows, ledger records transactions, and the math services each own one arithmetic operation.
- `docker-compose.yml`: local cluster wiring, including Postgres and service-to-service networking.
- `README.md` and `ARCHITECTURE.md`: system-level overview and intended service boundaries.

Request flow to keep in mind:

- Browser → API Gateway
- Gateway enforces JWT and rate limits, then proxies to private services
- Identity handles register/login/token issuance
- Billing talks to Xendit and accepts webhook callbacks
- Ledger stores transaction history asynchronously
- Frontend code should call the gateway, not the internal services directly

## Common commands

Install workspace dependencies:

```bash
pnpm install
```

Root workspace commands:

```bash
pnpm dev
pnpm build
pnpm lint
pnpm test
```

Local cluster:

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f
docker compose down
docker compose down -v
```

Frontend (`apps/web`):

```bash
pnpm --filter web dev
pnpm --filter web build
pnpm --filter web lint
pnpm --filter web test
```

Single frontend test:

```bash
pnpm --filter web test -- app/_components/dashboard-shell.test.tsx -t "name"
```

Python services (`services/api-gateway`, `services/identity`, `services/billing`, `services/ledger`, and the math services):

```bash
pnpm --filter billing dev
pnpm --filter billing lint
pnpm --filter billing test
```

Single Python test:

```bash
cd services/billing && pytest tests/test_billing_api.py::test_name
```

You can also pass pytest selectors through the pnpm script:

```bash
pnpm --filter billing test -- tests/test_billing_api.py::test_name
```

API docs when the stack is running:

```text
http://localhost:4000/docs
```

## Architecture notes

- The gateway is the only public HTTP entrypoint in the local stack. Internal services stay private behind Docker DNS.
- Authentication is centralized at the gateway instead of being duplicated in every worker.
- Billing has a webhook path that intentionally bypasses JWT checks so Xendit callbacks can reach the service.
- Each math worker is isolated per operation; treat them as independent deployable units.
- The web app is mostly shell/navigation/layout code plus thin API adapters and cookie/session helpers.
- Service configuration is env-driven and usually flows through per-service `config.py` helpers.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **MaaS** (1113 symbols, 2334 relationships, 91 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> Index stale? Run `node .gitnexus/run.cjs analyze` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? `npx gitnexus analyze` (npm 11 crash → `npm i -g gitnexus`; #1939).

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows. For regression review, compare against the default branch: `detect_changes({scope: "compare", base_ref: "master"})`.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `query({search_query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `context({name: "symbolName"})`.
- For security review, `explain({target: "fileOrSymbol"})` lists taint findings (source→sink flows; needs `analyze --pdg`).

## Never Do

- NEVER edit a function, class, or method without first running `impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit changes without running `detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/MaaS/context` | Codebase overview, check index freshness |
| `gitnexus://repo/MaaS/clusters` | All functional areas |
| `gitnexus://repo/MaaS/processes` | All execution flows |
| `gitnexus://repo/MaaS/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
