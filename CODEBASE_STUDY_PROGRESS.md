# MaaS Codebase vs. Manual Notes — Study Progress

_Assessed July 20, 2026 from the current `master` history, repository files, GitNexus flows, and a Graphify knowledge graph._

## Short answer

Your project has moved beyond a basic Docker/microservices exercise. You now have a working local SaaS-style system with a Next.js frontend, FastAPI microservices, centralized API gateway, JWT authentication, PostgreSQL persistence, Xendit billing, a transaction ledger, automated tests, CI workflows, Docker image delivery to ACR, Terraform-defined Azure VM/network infrastructure, and a local NGINX TLS reverse proxy.

Your latest **committed project progress** has three layers:

1. **Latest commit overall — documentation/runbook:** commit `788d240` on April 28, 2026 expanded `CLAUDE.md` with the project overview and common commands.
2. **Latest functional infrastructure work:** commit `23ec316` on April 18, 2026 added local NGINX reverse-proxy routing and SSL termination in `services/nginx/nginx.conf`.
3. **Latest major application feature:** the April 13, 2026 Xendit integration completed subscription/payment behavior, webhook processing, billing UI integration, payment-intent reuse, bounded activation polling, and validation/security tests.

Therefore, the most accurate description of where you stopped is:

> **You finished the core local application and payment flow, then began the edge/infrastructure layer by adding NGINX HTTPS termination.**

## Concepts demonstrated in code

### Clearly implemented

| Manual-notes concept | Evidence | Assessment |
|---|---|---|
| Python dependency management | Every backend service has separate `requirements.txt` and `requirements-dev.txt` files. | Complete for the current service structure. |
| Dockerfiles and `.dockerignore` | Each backend service has its own Dockerfile and `.dockerignore`. | Complete. |
| Docker Compose service networking | Services call internal DNS names such as `identity`, `billing`, `ledger`, and `postgres`. Only the API gateway is normally exposed to the host (`docker-compose.yml:7-10`). | Complete locally. |
| Compose startup dependencies | Identity, ledger, and billing wait for PostgreSQL's `service_healthy` condition (`docker-compose.yml:47-49`, `docker-compose.yml:81-83`, `docker-compose.yml:97-99`). | Complete for database-dependent services. |
| Database health checking | PostgreSQL uses `pg_isready`, with interval, timeout, and retry settings (`docker-compose.yml:116-120`). | Complete. |
| Persistent Docker storage | The `ledger_data` named volume persists PostgreSQL data (`docker-compose.yml:114-124`). | Complete. |
| API gateway | The gateway centralizes JWT checks, rate limiting, request IDs, service forwarding, billing access, and ledger publication. Its proxy helpers are the graph's most connected code nodes. | Strong implementation. |
| Microservices architecture | Separate identity, billing, ledger, and four math services sit behind the gateway. | Strong local implementation. |
| Authentication | Registration/login, password hashing, JWT issuance, protected routes, cookies/session handling, and frontend auth screens exist. | Strong implementation. |
| Billing/payment integration | Xendit subscription creation and webhook handling, callback-token validation, intent reuse, polling, billing status, and frontend billing UX exist. | Strong implementation and your latest major application milestone. |
| CI testing and linting | `.github/workflows/unit-tests.yaml` runs monorepo tests; `.github/workflows/lint.yaml` runs the lint task with Ruff and Node tooling. | Implemented. |
| Container registry/CD build | `.github/workflows/deploy-image.yaml` logs into Azure ACR and builds/pushes service images (`deploy-image.yaml:31`, `deploy-image.yaml:57`). | Implemented through image delivery; runtime deployment remains incomplete. |
| Terraform/IaC fundamentals | Terraform defines an Azure resource group, VNet, subnet, public IP, NSG, NIC, Linux VM, and ACR (`infra/terraform/main.tf:32-248`). | Strong first infrastructure slice. |
| Azure networking fundamentals | VNet, subnet, NSG, NIC, and public IP are represented directly in Terraform. | Implemented in code even though the notes remain unchecked. |
| NGINX reverse proxy | NGINX has frontend/backend upstreams and routes `/` to the frontend and `/api/` to the gateway (`services/nginx/nginx.conf:56-67`). | Implemented as a local-development configuration. |
| SSL/TLS termination | Port 80 redirects to HTTPS; port 443 terminates TLS using local certificates (`services/nginx/nginx.conf:39-53`). | Partially complete: local/self-signed only, not production certificate lifecycle management. |

### Partially implemented

| Concept | Current boundary |
|---|---|
| Git flow | The history shows feature branches and merged PRs, but this assessment did not find a documented/practiced rebase and cherry-pick learning track. |
| Reverse proxy | Routing and TLS termination exist, but NGINX is not integrated into the current `docker-compose.yml`, and the config itself identifies missing production hardening, logging, monitoring, compression, and trusted certificates. |
| CI/CD deployment | CI and ACR image pushes exist. There is no completed automated deployment from ACR into the Terraform-created VM or an AKS runtime. |
| Terraform | Resources are defined, but there is no remote backend/state-locking configuration, modular environment structure, AKS, managed PostgreSQL, or Key Vault. |
| Container orchestration | Docker Compose coordinates the local system, but Kubernetes/AKS orchestration has not started. |
| Observability | Application logging exists in places, but no centralized logs, metrics, tracing, dashboards, or alerting stack exists. |
| Secret management | GitHub secrets and environment variables are used, but runtime secrets are not sourced from Azure Key Vault or managed identities. |

### Still absent or primarily conceptual

- Terraform remote state and locking
- Azure Blob Storage backend
- AKS/Kubernetes resources and deployment manifests
- Horizontal scaling and rolling deployment policies
- Managed PostgreSQL in Azure
- Azure Key Vault and managed identities
- Azure Monitor/Log Analytics
- Prometheus/Grafana metrics and alerting
- Production certificate issuance/renewal
- NGINX production hardening, compression, caching, and operational logging
- Load balancing across multiple application replicas

## Notes checklist corrections suggested by the code

Your checklist under `MANUAL_NOTES.md:149-169` understates what you have already practiced. Based on the repository, these can reasonably be updated:

- **Container Registries (ACR):** complete or at least practiced — Terraform creates ACR and GitHub Actions pushes images.
- **Virtual Networks (VNet):** practiced — Terraform resource exists.
- **Subnets:** practiced — Terraform resource exists.
- **Network Security Groups (NSG):** practiced — Terraform resource and inbound rules exist.
- **Network Interfaces (NIC):** practiced — Terraform resource and NSG association exist.
- **Public IPs:** practiced — Terraform resource exists.
- **Reverse Proxies:** stronger than `[/]` for local development, although production operations remain incomplete.
- **SSL/TLS Certificates:** partial — you understand termination and local certificates, but not trusted issuance and renewal yet.
- **Microservices Architecture:** should be marked complete at the implementation-foundation level.
- **API Gateways:** correctly marked complete and is one of the project's strongest areas.
- **CI/CD Pipelines and GitHub Actions:** correctly marked complete at the current VM/ACR stage, although cluster deployment remains a future level.

## Recommended next self-study concept

# Terraform state management with an Azure Blob remote backend

This is the best immediate next topic—not AKS yet.

### Why this is the right next step

1. **It is the first unchecked cloud concept in your notes** (`MANUAL_NOTES.md:149`).
2. **It directly extends infrastructure you already wrote.** You already define a VM, network, NSG, NIC, public IP, and ACR; state is how Terraform remembers and safely changes those resources.
3. **It closes a real production gap.** A local `terraform.tfstate` is unsuitable for CI/CD or team usage.
4. **It prepares the path to AKS.** Adding a large resource such as a Kubernetes cluster before understanding state, locking, drift, and recovery would make failures harder to reason about.
5. **It naturally connects your existing GitHub Actions and Azure work.** Your pipeline can run `terraform plan` against shared state after authentication is improved.

### Study goals

Learn these in order:

1. What Terraform state records and why deleting it does not delete Azure resources.
2. Desired configuration vs. Terraform state vs. real cloud state.
3. Resource addressing, dependency references, refresh, and drift detection.
4. Sensitive values in state and why state storage requires strict access control.
5. Azure Blob Storage as an `azurerm` backend.
6. State locking/concurrent-run protection and CI safety.
7. `terraform state list`, `state show`, `import`, `moved`, and safe recovery workflows.
8. Separating bootstrap infrastructure for the state backend from the main MaaS infrastructure.

### Practical MaaS exercise

Build a small Terraform bootstrap layer that creates:

- one storage account;
- one private blob container for Terraform state;
- access controls suitable for your deployment identity;
- a backend configuration for the existing MaaS stack;
- a documented migration from local state to remote state;
- a CI plan job that cannot mutate infrastructure on pull requests.

Then deliberately change one harmless Azure property outside Terraform, run `terraform plan`, and observe how drift appears. This will turn “state files” from a definition into an operational concept.

### Recommended sequence after that

1. **Terraform state + Azure Blob backend**
2. **Azure identity: service principals, RBAC, then managed identity/OIDC**
3. **Key Vault secret management**
4. **Deploy the current Compose stack to the existing VM**
5. **Centralized logging and basic Azure Monitor visibility**
6. **Only then begin Kubernetes fundamentals and AKS**

This sequence lets you finish the VM-based deployment path you already started before adding the operational complexity of Kubernetes.

## Documentation drift worth fixing later

`README.md` still labels some already-created capabilities—particularly CI and Terraform—as planned/TBD. `ARCHITECTURE.md` also describes AKS, managed PostgreSQL, remote state, Key Vault, and Prometheus/Grafana as if they are part of the target architecture. Treat those as the intended destination, not the current deployed state.

## Graphify audit note

The generated graph contains 778 nodes, 1,257 built edges, and 56 communities. Its integrity check reported 216 dangling inferred/reference endpoints and 26 same-endpoint edge collapses. The graph remains useful for navigation, but inferred “surprising connections” should be treated as leads rather than verified facts. The implementation conclusions above were cross-checked against repository files, Git history, and GitNexus rather than relying on inferred graph edges alone.
