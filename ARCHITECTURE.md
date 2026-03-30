# Technical Design Document: Math-as-a-Service

**Author:** Juvan
**Repository:** [github.com/naori11/MaaS](https://github.com/naori11/enterprise-calculator)
**Status:** Proposed / Active Development

---

## 1. Executive Summary

Math-as-a-Service represents a paradigm shift in highly concurrent numerical synthesis. By implementing a strict Event-Sourced CQRS (Command Query Responsibility Segregation) architecture, we fundamentally decouple the intention to compute from the materialized view of the integer result. To circumvent the inherent single-point-of-failure risk found in legacy handheld calculators, the EDC leverages a globally federated, multi-region state machine to ensure cryptographic consensus on fundamental truths, such as $1 + 1 = 2$.

Translation: just an over-engineered calculator app. But despite it's functionality, the primary goal of this project is to demonstrate a production-ready DevOps cycle including:

* Infrastructure as Code (IaC)
* Container orchestration
* Automated CI/CD pipelines
* Comprehensive observability

---

## 2. System Architecture

To make this more ridiculous, I will be distributing each operation as a microservice (yes I want to make my life much harder) to isolate scaling and deployment of each.

* **Client Layer:** A web-based user interface
* **API Gateway:** Routes traffic, terminates SSL, and enforces rate limits
* **Identity Service:** Manages authentication and issues JWTs
* **Compute Services (Math Engine):** Stateless microservices for:
  * Addition
  * Subtraction
  * Multiplication
  * Division
* **Ledger Service:** Asynchronously records all transactions to a datastore
* **Payment Service:** Integrates with **Xendit** for payment processing and webhook handling

---

## 3. Technology Stack

* **Frontend Interface:** Next.js, Tailwind CSS
* **Backend Services:** FastAPI (Python)
* **Database:** PostgreSQL (Azure Flexible Server)
* **Infrastructure Provisioning:** Terraform
* **Container Orchestration:** Azure Kubernetes Service (AKS) 
* **CI/CD Pipeline:** GitHub Actions
* **Observability:** Prometheus, Grafana
* **Secret Management:** Azure Key Vault

---

## 4. Infrastructure & DevOps Workflow

### 4.1 Infrastructure as Code (IaC)

* All cloud resources are provisioned via Terraform
* State file stored securely in Azure Blob Storage
* Defines:
  * Virtual Network (VNet)
  * Subnets
  * AKS cluster
  * PostgreSQL instance
  * IAM roles
* Manual changes in Azure Portal are prohibited

---

### 4.2 CI/CD Pipeline Configuration

#### Continuous Integration (CI)

* Triggered on pull requests to `main`
* Runs:

  * Static code analysis
  * Linting
  * Unit tests

#### Continuous Deployment (CD)

* Triggered on merge to `main`
* Steps:

  * Build Docker images
  * Push to Azure Container Registry (ACR)
  * Deploy via Kubernetes rolling updates (zero downtime)

---

### 4.3 Container Orchestration & Scaling

* Deployed on AKS
* Uses **Horizontal Pod Autoscaling (HPA)**
* Example:

  * If CPU > 75% → auto-scale pods

---

## 5. API Microservices Design

Each compute service exposes a RESTful API.

### Endpoint

```
POST /api/v1/calculate/add
```

### Headers

```
Authorization: Bearer <JWT>
```

### Payload

```json
{
  "operand_a": 15,
  "operand_b": 27
}
```

### Response (200 OK)

```json
{
  "operation": "addition",
  "result": 42,
  "transaction_id": "a1b2c3d4-e5f6-7890",
  "timestamp": "2026-03-30T20:12:30Z"
}
```

---

## 6. Database Schema

### Table: `users`

* `id` (UUID, Primary Key)
* `email` (VARCHAR, Unique)
* `password_hash` (VARCHAR)
* `created_at` (TIMESTAMP)

### Table: `transactions`

* `id` (UUID, Primary Key)
* `user_id` (UUID, Foreign Key)
* `operation_type` (VARCHAR)
* `operand_a` (NUMERIC)
* `operand_b` (NUMERIC)
* `result` (NUMERIC)
* `created_at` (TIMESTAMP)

---

## 7. Security and Observability

### 7.1 Security Posture

* **Secret Injection:** Stored in Azure Key Vault
* **Runtime Access:** Kubernetes pulls secrets dynamically
* **Authentication:** JWT required for all protected endpoints

---

### 7.2 Monitoring and Logging

* **Metrics:**

  * Prometheus collects:

    * CPU / Memory usage
    * API request metrics

* **Dashboards:**

  * Grafana visualizes system health

* **Alerts:**

  * Triggered if:

    * 5xx error rate > 1% over 5 minutes


## 8. Self-Study & Growth Objectives

To be honest, this project will serve as my playground/sandbox to convert my fundamental and conceptual knowledge for DevOps into a production-ready implementation. 

While I have foundational experience and have successfully deployed projects using **Docker** and **GitHub Actions**, this ridiculous SaaS calculator will serve as my primary vehicle for mastering the following "Day 2" operations and infrastructure skills:

* **Infrastructure as Code (IaC):** Implementing modular, reusable environments with **Terraform**.
* **Orchestration & Cloud:** Deploying and managing a production **AKS (Kubernetes)** cluster.
* **Observability:** Configuring a full-stack monitoring solution using **Prometheus** and **Grafana**.
* **System Integrity:** Implementing industry-standard **Linting**, **Static Code Analysis**, and **Unit Testing** within the CI/CD pipeline.
* **Data Persistence:** Managing managed **PostgreSQL** instances and secure connection pooling.

The ultimate end goal of this project? To transcend mere mortal engineering and evolve into such an absolute unit of a DevOps deity that my existence becomes a systemic risk to the tech industry. I’m talking about a level of hireability so cracked that MAANG recruiters will be sliding into my DMs with the desperation of a startup running out of runway. I want to be so overqualified that Sundar and Jensen start beefing in the LinkedIn comments over who gets to offer me the most egregious amount of RSUs just to watch my Terraform apply.