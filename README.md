# Math-as-a-Service (MaaS)

A microservices-based SaaS Math API designed to demonstrate production-grade DevOps practices while delivering secure, scalable math operations through a single API gateway (AKA a calculator app on crack).

This repository implements the local microservices cluster (FastAPI + Docker Compose) and maps to a broader architecture that includes cloud deployment, IaC, CI/CD, and observability.

---

## Project Overview

MaaS exposes authenticated math APIs and subscription capabilities through an API Gateway, with internal services for identity, billing, and ledgering.

### Current local capabilities

- API Gateway routing and centralized JWT enforcement
- Identity service (`register`, `login`, `me`)
- Billing service with Xendit invoice creation + webhook handling
- Ledger service for async transaction ingestion and retrieval
- Isolated math worker services (add/subtract/multiply/divide)
- PostgreSQL-backed persistence via Docker Compose

### Strategic architecture vision

The architecture blueprint (`ARCHITECTURE.md`) targets a full DevOps platform including Terraform-provisioned Azure infrastructure, AKS deployment, GitHub Actions CI/CD, and Prometheus/Grafana observability.

---

## Architecture at a Glance

- **Client Layer**
  - Web frontend for user interaction and API consumption **[TBD] (Planned)**
- **API Gateway** (`services/api-gateway`)
  - Single public ingress (`localhost:4000`)
  - Routes traffic to internal services over Docker network
  - Enforces rate limiting and JWT auth for protected routes
- **Identity Service** (`services/identity`)
  - User registration and login
  - JWT issuance and identity lookup
- **Billing Service** (`services/billing`)
  - Subscription status and upgrade flow
  - Xendit invoice integration
  - Webhook processing endpoint for payment confirmation
- **Ledger Service** (`services/ledger`)
  - Asynchronous ingestion of compute events
  - Query endpoint for transaction history
- **Math Engine Workers**
  - `services/math-add`
  - `services/math-subtract`
  - `services/math-multiply`
  - `services/math-divide`
- **Data Layer**
  - PostgreSQL container with health checks and persistent volume

---

## Core Data Flow & Security Model

### 1) API Gateway Offloading Pattern (JWT)

The gateway is the security boundary:

- Protected routes require `Authorization: Bearer <JWT>`
- JWT verification is centralized at the gateway
- Internal services are reached via private container DNS names

This avoids duplicate auth logic across all workers and keeps policy consistent.

### 2) Internal Docker Routing (Hidden Workers)

Only the gateway exposes a host port by default.

- Internal services communicate via Docker network hostnames (`http://identity:8000`, `http://math-add:8000`, etc.)
- Compute, billing, identity, and ledger services are not publicly exposed in local compose
- PostgreSQL external port is intentionally not exposed by default

### 3) Xendit Webhook Bypass Path

`POST /api/v1/billing/webhook/xendit` bypasses JWT checks at the gateway so external Xendit callbacks can be processed.

- Gateway forwards webhook request to billing service
- Billing validates `x-callback-token` against `XENDIT_CALLBACK_TOKEN` when configured

---

## Prerequisites & Environment

## Prerequisites

- Docker Desktop (or Docker Engine + Compose plugin)
- Git
- A local `.env` file in repository root

## Environment setup

1. Copy example env file:

```bash
cp .env.example .env
```

2. Replace placeholder values with secure secrets.

### Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `JWT_SECRET` | Yes | JWT signing/verification secret |
| `XENDIT_SECRET_KEY` | Yes | Xendit API key for invoice creation |
| `POSTGRES_USER` | Yes | Postgres username |
| `POSTGRES_PASSWORD` | Yes | Postgres password |
| `XENDIT_CALLBACK_TOKEN` | Recommended | Webhook callback token verification |
| `JWT_ALGORITHM` | Optional | JWT algorithm (default `HS256`) |
| `JWT_EXPIRES_SECONDS` | Optional | Token TTL for identity service |
| `RATE_LIMIT_REQUESTS` | Optional | Gateway rate-limit threshold |
| `RATE_LIMIT_WINDOW_SECONDS` | Optional | Gateway rate-limit window |
| `UPSTREAM_TIMEOUT_SECONDS` | Optional | Gateway upstream timeout |
| `LEDGER_PUBLISH_TIMEOUT_SECONDS` | Optional | Gateway async ledger publish timeout |
| `LEDGER_DEFAULT_LIMIT` | Optional | Default ledger query limit |
| `LEDGER_MAX_LIMIT` | Optional | Max ledger query limit |
| `LEDGER_QUEUE_MAXSIZE` | Optional | Ledger ingest queue size |

> Security note: never commit `.env` or real secrets. Use sandbox/test keys for local development.

---

## Local Runbook (Docker Compose)

From repository root:

### Build images

```bash
docker compose build
```

### Start cluster

```bash
docker compose up -d
```

### Rebuild and start

```bash
docker compose up -d --build
```

### Check status

```bash
docker compose ps
```

### View logs

```bash
docker compose logs -f
```

### Stop and remove containers

```bash
docker compose down
```

### Stop and remove containers + volumes (fresh DB state)

```bash
docker compose down -v
```

### Postgres health checks

`postgres` uses `pg_isready` health checks. `identity`, `billing`, and `ledger` wait on `service_healthy`, reducing startup race conditions.

---

## API Documentation

When the cluster is running, interactive OpenAPI docs are available at:

- **http://localhost:4000/docs**

---

## Roadmap / TBD

The following items are part of the architecture blueprint and are included intentionally as planned work.

- **Frontend client layer (Next.js + Tailwind)** **[TBD] (Planned)**
- **Terraform-managed Azure infrastructure (VNet, subnets, IAM, AKS, PostgreSQL)** **[TBD] (Planned)**
- **Remote Terraform state in Azure Blob Storage** **[TBD] (Planned)**
- **AKS production deployment and rolling updates** **[TBD] (Planned)**
- **Horizontal Pod Autoscaling policy (e.g., CPU > 75%)** **[TBD] (Planned)**
- **GitHub Actions CI (lint, static analysis, unit tests on PR)** **[TBD] (Planned)**
- **GitHub Actions CD (build, push to ACR, deploy to AKS)** **[TBD] (Planned)**
- **Prometheus + Grafana dashboards and alerting** **[TBD] (Planned)**
- **Azure Key Vault–driven secret management in runtime** **[TBD] (Planned)**

---

## Repository Structure

```text
services/
  api-gateway/
  identity/
  billing/
  ledger/
  math-add/
  math-subtract/
  math-multiply/
  math-divide/
docker-compose.yml
ARCHITECTURE.md
```

---

## Status

**Status:** Active development.  
Implementation follows the architecture blueprint incrementally, with local Docker cluster capabilities available now and cloud/DevOps platform features marked as **[TBD] (Planned)**.
