# Cloud & DevOps Manual Notes

---

## 📑 Table of Contents

- [Part 1: Environment & Dependency Management](#part-1-environment--dependency-management)
  - [Managing Dependencies (python based backend)](#managing-dependencies-python-based-backend)
- [Part 2: Containerization & Local Orchestration (Docker)](#part-2-containerization--local-orchestration-docker)
  - [Creating Dockerfiles](#creating-dockerfiles)
  - [Testing Dockerfiles (Building and Running docker images)](#testing-dockerfiles-building-and-running-docker-images)
  - [Docker Compose](#docker-compose)
- [Part 3: Infrastructure as Code (Terraform)](#part-3-infrastructure-as-code-terraform)
  - [Terraform (IaC - Infrastructure as Code)](#terraform-iac---infrastructure-as-code)
  - [Terraform State Management](#terraform-state-management)
  - [Key CLI commands](#key-cli-commands)
- [Part 4: Cloud Platform & Identity Management (Azure)](#part-4-cloud-platform--identity-management-azure)
  - [Azure Blob](#azure-blob)
  - [Azure Identity](#azure-identity)
  - [Azure Key Vault](#azure-key-vault)
  - [SSH Keygen](#ssh-keygen)
- [Part 5: CI/CD Pipelines & Automation (GitHub Actions)](#part-5-cicd-pipelines--automation-github-actions)
  - [Azure Container Registry (ACR)](#azure-container-registry-acr)
  - [GitHub Actions](#github-actions)
- [Part 6: Backend, Ingress & Networking Architecture](#part-6-backend-ingress--networking-architecture)
  - [API Gateways](#api-gateways)
  - [Reverse Proxy (Ingress Layer)](#reverse-proxy-ingress-layer)
  - [NGINX](#nginx)
  - [Microservices Architecture](#microservices-architecture)
  - [SSL/TLS Certificates](#ssltls-certificates)
- [Part 7: Virtual Machine Deployment & Host Automation](#part-7-virtual-machine-deployment--host-automation)
  - [Cloud-Init & VM Provisioning](#cloud-init--vm-provisioning)
  - [VM Container Registry Access (ACR & Managed Identity)](#vm-container-registry-access-acr--managed-identity)
  - [Reliable Deployments with systemd](#reliable-deployments-with-systemd)
  - [Continuous Deployment (CD) Pipelines to VM](#continuous-deployment-cd-pipelines-to-vm)
- [Part 8: Azure Observability (Monitor & Log Analytics)](#part-8-azure-observability-monitor--log-analytics)
  - [The Concept of Centralized Logging](#the-concept-of-centralized-logging)
  - [Ingesting Docker Logs](#ingesting-docker-logs)
  - [Kusto Query Language (KQL)](#kusto-query-language-kql)
  - [Application Insights](#application-insights)
- [Part 9: Notes to Self & Career Roadmap](#part-9-notes-to-self--career-roadmap)
  - [Refresh on Networking Concepts](#refresh-on-networking-concepts--bro-you-know-all-of-these-from-3rd-year)
  - [Cloud Concepts](#cloud-concepts)
  - [Linux Commands & Concepts](#linux-commands--concepts)
  - [Additional DevOps & Backend Concepts](#additional-devops--backend-concepts)
  - [Career Advice & Transition Suggestions](#career-advice--transition-suggestions)

<div style="page-break-after: always;"></div>

---

# Part 1: Environment & Dependency Management

[▲ Back to Table of Contents](#-table-of-contents)

## Managing Dependencies (python based backend)

### For python based APIs:

- To create the requirements.txt file, use
  - `python -m venv venv` (create a virtual environment)
  - `pip install` the necessary dependencies
  - `pip freeze > requirements.txt`
  - or to automatically fetch the necessary dependencies (static code analysis), use `pipreqs` | `pip install pipreqs` | `pipreqs . --force`

- To separate test file dependencies (for github actions unit test)
  - create a separate `requirements-dev.txt` file
  - put dependencies mainly for testing only (pytest, httpx)
  - standard dependencies for testing in python is pytest and httpx

<div style="page-break-after: always;"></div>

---

# Part 2: Containerization & Local Orchestration (Docker)

[▲ Back to Table of Contents](#-table-of-contents)

## Creating Dockerfiles

- Dockerfile notes are commented under each dockerfile within this project.
- Always create a `.dockerignore` file. Put the files unnecessary for the deployed state such as unit tests, python caches, venv, `.git` and `.gitignore` files.

### Testing Dockerfiles (Building and Running docker images)

- `docker build -t 'image_name':'tag' .` | command for building the image based on dockerfile. Must run within the directory of the app.
- `docker run -p 'host_port':'container_port' 'image_name'` | command for running the image. Add `-d` before image name to detach terminal.
- `docker ps` / `docker ps -a` | command to list running/dead or exited containers
- `docker stop 'container_id'` | shuts down a running container
- `docker rm 'container_id'` | removes the container build
- `docker system prune` | removes every image/build that are unused
- `docker exec -it 'container_id' /bin/sh` or `/bin/bash` | opens a live terminal within the container

## Docker Compose

- Should be made after creating the initial services within the codebase (core business logic)
- Docker compose file should grow alongside the codebase.
- Dockerfile notes are commented under the `docker-compose.yml` file within this project.
- For environment variable injection for container routing, use the service name within the docker network (ex. `http://math-add:8000`)

---

- For pulling images (such as database images):
  - Env variables for database config would be set under the `environment:` tag, whichever is necessary.
  - Use `volumes:` to define where to store data when containers or images is stopped or remove.
    - Right side part is always based on the image, then left is custom.
  - When setting volumes, you have to redefine the volume tag along with the name of the volume that you set onto the end of the dockerfile. This tells the docker engine that this volume should persist independently of any container.
    - `volumes:`
      - `'volume_name':`

---

- For issues such as the database image loading slower than the services that requires it:
  - instead of calling the image name normally (e.g. - postgres), do the following:

  - for the postgres image itself:

    ```yaml
    healthcheck:
      test: ["shell", "command"] # Command to test database status (depends on database image pulled)
      interval: # Number of times to test
      timeout: # Time to consider as failed test
      retries: # Number of times to retry command
    ```

  - for images that requires to connect to the postgres image:
    ```yaml
    postgres:
      condition: service_healthy # Make sure that the image is healthy before spinning up the service.
    ```

- For needing to run specific commands within the dedicated service/image, use `docker compose exec 'service_name' 'command'`

<div style="page-break-after: always;"></div>

---

# Part 3: Infrastructure as Code (Terraform)

[▲ Back to Table of Contents](#-table-of-contents)

## Terraform (IaC - Infrastructure as Code)

- Made after creating the initial services cluster (the API.)
- `terraform init` | command for preparing terraform directory (`.terraform`). Donwloads necessary provider plugins (defined under `terraform/required_providers` block)
- `terraform plan` | command that shows terraform execution plan to the actual infrastructure platform
- `terraform apply` | applies the IaC by spinning up the resources defined within the code along with its configurations
- `terraform destroy` | removes everything that is defined within the terraform configuration
- `terraform fmt` | formats your code to make it more clean

## Terraform State Management

- Terraform state (`.tfstate`) file is a JSON file that tracks the resources created by Terraform the last time the `terraform apply` command was run.
- It is used by Terraform to keep track of the resources (as a lookup table) it has created and to ensure that the infrastructure matches the desired state defined in the code.

### Scenarios & Questions

> **Scenario 1:** If you manually delete a Virtual Network in the Azure Portal, but don't touch your Terraform code or state file, what happens the next time you run `terraform plan`? Why?
>
> - Terraform will perform a background refresh by checking the `.tfstate` file for the existing resources, then calls Azure API for each resource to verify its existence.
> - Then terraform will detect that the resource no longer exists.
> - If the resource is still within the `.tf` file, the next time that `terraform apply` is run, it will attempt to create the resource again.

> **Scenario 2:** If you delete your local `terraform.tfstate` file, but the Azure resources still exist, what happens the next time you run `terraform apply`?
>
> - Terraform will not have any state to compare against, so it will treat the resources as not existing and attempt to create them again.
> - But since all of the resources still exist in Azure, and there is no lookup table to compare with, Azure would return rejected requests.
> - It does not recreate the state file, so the next time you run `terraform apply`, it will still treat the resources as not existing. The only way to fix this is to either delete the resources from Azure or recreate the state file by importing them into Terraform using `terraform import`.

> **If Developer A and Developer B both run `terraform apply` from their own laptops at the exact same time using local state, what is the risk to the Azure environment?**
>
> - Multiple API calls to create resources will be sent and could cause conflicts, duplicate resources, and broken tfstate files for both ends.

> **Why can’t you just commit `terraform.tfstate` to Git to solve the collaboration problem? (Hint: There are two major reasons—one relates to merging, the other to security).**
>
> - Merge conflicts, and tfstate files contains secrets such as ssh keys, admin passwords, API tokens, etc. On which, everything is stored as plaintext, and Azure Blob storage is the one encrypthing it.

> **How does Terraform provision the resource needed for the remote state file if it does not exist yet?**
>
> - You provision it manually using the Azure portal or CLI.
> - Through bootsrapping. Create a separate Terraform configuration file first in a separate directory which provisions the storage account and container for the remote state file. Then you can run `terraform init` in the main directory to use the remote state file.

## Key CLI commands

- `terraform state list`: Lists all resources in the state file.
- `terraform state show <resource>`: Shows the details of a specific resource in the state file.
- `terraform import <resource> <id>`: Imports an existing resource from Azure into the state file in cases of people adding resources manually.
- `terraform state rm <resource>`: Removes a resource from the state file without deleting it from Azure.
- `terraform state mv <old_resource> <new_resource>`: Renames a resource in the state file.

<div style="page-break-after: always;"></div>

---

# Part 4: Cloud Platform & Identity Management (Azure)

[▲ Back to Table of Contents](#-table-of-contents)

## Azure Blob

- Azure Blob Storage is a service that allows you to store unstructured data such as logs, backups, and media files.
- Has a Blob Lease feature that allows you to lock a file (a blob) when it is being used by a resource, such as terraform's state files to prevent other resources from modifying it until it is done.

## Azure Identity

- Identities assigned to entities such as human identities, or pipelines/services.
- It is used by Azure services to authenticate and authorize access to resources.

### Traditional Active Directory vs Microsoft Entra ID

- **Traditional Active Directory** is on premises, while **Microsoft Entra ID** (formerly Azure Active Directory) is cloud-based.

### App Registration vs Enterprise Application

- **App Registration:**
  - A global definition/blueprint for the app.
  - Stored in the home tenant where the app is built.
  - Generates the `Application ID` (Client ID) and manages credentials (client secrets/certificates).
  - It handles `Authentication`.
- **Enterprise Application:**
  - The local representation of the application inside a specific tenant. (Another tenant might be another company's tenant.)
  - Represents the identity (the app itself) that gets assigned Azure RBAC roles, user-assignment policies, and Conditional Access.
  - It handles `Authorization`.
  - Enterprise application holds the actual RBAC roles and sign in logs.
  - _Rule of thumb:_ 1 App Registration can have multiple Enterprise Applications across different customer tenants (Multi-tenant SaaS).

### Entra Roles vs Azure RBAC

- **Entra Roles (Directory Level):** Govern Entra ID objects.
  - Examples: _Global Administrator_, _User Administrator_, _Application Administrator_.
  - Actions: Reset user passwords, create security groups, verify custom domains.
- **Azure RBAC (ARM / Infrastructure Level):** Govern Azure cloud resources.
  - Examples: _Owner_, _Contributor_, _Storage Blob Data Contributor_.
  - Actions: Restart VMs, read Key Vault secrets, deploy ARM/Bicep templates.

### Service Principal (Basically the same as Enterprise Application)

- Service principal is a type of identity that represents an app or service, not a user.
- It is used to authenticate and authorize access to Azure resources on behalf of the app or service, such as a VM instance, CI/CD pipeline runners, or other Azure services.

### Azure RBAC vs Microsoft Entra ID

- Microsoft Entra ID is used to manage access to Azure resources at the `directory level`, such as assigning RBAC roles to groups of users or service principals.
  - Sample: Global Administrator, User Administrator, Application Administrator
  - Create new user accounts, reset passwornds, register new apps, manage group memberships, etc.
- Azure RBAC (Role-Based Access Control) is used to manage access to Azure resources at the `resource level`.
  - Sample: Contributor, Reader, Storage Blob Data Contributor, AcrPull.
  - Deploy VMs, read secrets from Key Vault, pull container images, create databases, etc.

### Common Built-in Roles

- Azure splits actions into two planes:
  - Control Plane (Management): Managing the resource itself, such as starting a VM, resizing a storage account, or deleting a resource.
  - Data Plane: Accessing the actual data inside a resource, such as reading secrets from Key Vault, reading rows in a database, pulling images from ACR.

| Built-in Role          | Plane         | What It Can Do                                       | What It Cannot Do                                     |
| ---------------------- | ------------- | ---------------------------------------------------- | ----------------------------------------------------- |
| Reader                 | Control Plane | View existing resources and configurations           | Make any changes or read sensitive data payloads      |
| Contributor            | Control Plane | Create, update, restart, and delete resources        | Grant/modify permissions (RBAC) to other users        |
| Owner                  | Control Plane | Full management access + grant permissions to others | —                                                     |
| AcrPull                | Data Plane    | Pull container images from Azure Container Registry  | Push images, delete repositories, manage ACR settings |
| Key Vault Secrets User | Data Plane    | Read secret values inside a Key Vault                | Create or delete the Key Vault resource itself        |

### Scope Hierarchy

```text
Management Group
 └── Subscription
      └── Resource Group
           └── Individual Resource
```

- Management Group: Managing access, policies, and compliance for multiple subscriptions.
- Subscription: Biling and operational boundary.
- Resource Group (RG): Logical container for resources, used for managing access, policies, and compliance sharing the same lifecycle.
- Individual Resource: A specific Azure resource, such as a VM, storage account, or database.

## Managed Identities

- Makes it easier to manage access to Azure resources without hardcoding credentials.
- It transforms manual credential management into a more automated and secure process (similar to having a badge that verifies your identity)
- It gives your code hosted in a VM access to Azure resources without needing to store credentials in the VM.
- Basically, a service (Azure Instance Metadata Service [IMDS]) is listening within Azure's hypervisor. It is used and accessed by the VMs to provide identity and access to Azure resources. The application code requests for a short lived Microsoft Entra ID token that they use to authenticate with Azure services.

### User Assigned vs System Assigned Managed Identity

- User Assigned:
  - 1 is to many resources.
  - Created as an independent resource in a resource group.
  - Existence is independent of the resource it is assigned to.
- System Assigned:
  - 1 is to 1 resource.
  - Enabled directly as a toggle on the Azure Resource.
  - If resource is deleted, the identity is automatically removed.

## OpenID Connect (OIDC) for GitHub Actions

- Usually, connecting GitHub actions to Azure resources requires a service principal or managed identity with a client secret and pasting it directly into the GitHub Repository Secrets.
- But instead, you can use OIDC to authenticate without a client secret.
- OIDC works through the following process:
  - A GitHub Actions workflow triggers GitHub's internal token service for a OIDC JWT token.
  - GitHub signs the token using its private key that contains information about the repository, organization, git ref, and other metadata.
  - The signed token is sent to Azure through Microsoft Entra ID.
  - Entra ID uses GitHub's public key to verify the token.
  - If the token is verified, Entra ID responds with an access token that disappears once the GitHub Actions workflow is complete.

## Azure Key Vault

- Azure Key Vault is a cloud-based service that allows you to store and manage cryptographic keys and secrets instead of manually storing them in your repository.
- Applications would then safely fetch secrets from Azure Key Vault through HTTPS via authentication using Azure Identity.
- Using Azure Key Vault allows you to set least privilege access control for your secrets, only allowing access to the necessary secrets.

### Objects within Azure Key Vault

- **Secrets:**
  - Values typically injected within your application's environment.
  - Database connection strings, JWT secrets, API keys.
  - Usually stored as plaintext value through `.env` files or environment variables.
- **Keys:**
  - Asymmetric key pairs (public/private) used for encryption/decryption.
- **Certificates:**
  - SSL/TLS certificates, API Gateway domains.
  - Public certificates used for verifying the identity of a service or user.

### Management Plane vs Data Plane

- **Management Plane:**
  - Management plane is responsible for managing the lifecycle of resources, including provisioning, scaling, and monitoring.
  - In Key Vault, management plane refers to the CRUD of the Key Vault itself, network firewalls, and resource tags.
- **Data Plane:**
  - Data plane is responsible for the actual data processing and storage.
  - Refers to the CRUD of the actual secrets stored in the Key Vault.

### Built-in RBAC Roles

- **Key Vault Administrator:**
  - Full management of data plane and permissions.
- **Key Vault Secrets Officer:**
  - Access to read, write, and delete secrets.
- **Key Vault Secrets User:**
  - Access to read secrets only.

### RBAC Bootstrap & depends_on Race Condition

- When creating a Key Vault with RBAC, no one would have data plane access by default.
- The Service Principal used to create the Key Vault (Management Plane) may not have the necessary permissions to perform CRUD operations on the Key Vault (Data Plane).
- The Service Principal should have atleast the `Key Vault Secrets Officer` role assigned to it to ensure it can perform CRUD operations on the Key Vault.
- In Terraform, the `azurerm_key_vault_secret` resource must explicitly declare `depends_on = [azurerm_role_assignment.tf_kv_officer]`:
  - Without `depends_on`, Terraform may attempt to write the secret before the role
    assignment is created or before Entra ID role replication finishes (10–60s delay), causing
    a `403 Forbidden`.

### Injecting Secrets into the App

- Secrets stored in Azure Key Vault can be accessed through:
  - Direct SDK Integration: ([Azure Key Vault SDK](https://docs.microsoft.com/en-us/azure/key-vault/)) (Application code direct integration)
  - Deployment-Time Injection: Through the spin-up of a VM instance using a managed identity or Azure CLI.
    - Managed Identity: The VM instance is assigned a managed identity, which can be used to authenticate with Azure Key Vault.
    - Azure CLI: The VM instance is authenticated using the Azure CLI, which can be used to authenticate with Azure Key Vault.

## SSH Keygen

- `ssh-keygen -t rsa -b 4096 -C "sample@email.com"` | command for creating an SSH key pair for your local machine
- When command is run, it generates an `id_rsa.pub` (public key) and `id_rsa` (private key)
- Layman concept: `id_rsa.pub` is the lock and `id_rsa` is your key to the lock. You provide the lock in a VM instance.
- When you try to connect via SSH, your local machine uses the key to verify the signature based on the lock provided. Once verified, you will be given access to the VM without entering a password.

<div style="page-break-after: always;"></div>

---

# Part 5: CI/CD Pipelines & Automation (GitHub Actions)

[▲ Back to Table of Contents](#-table-of-contents)

## Azure Container Registry (ACR)

- Basically storage of Docker Images to be deployed within the VM
- Docker images are built within Github Actions (CI/CD) and pushed within ACR
- `admin_enabled` is set as true to have a username and password credentials to put within Github Actions secrets

## GitHub Actions

- Ideal pipelines for development:
  - Pull Requests:
    - Linting and Formatting (Did the developer follow the team's style guide? (e.g., no messy spacing, correct variable casing). If it fails, block the PR.)
    - Unit Testing (Unit tests made for each service)
    - Security Check (Are there any hardcoded passwords or glaring SQL injection vulnerabilities?)
  - Commit to Prod/Main Branch
    - Retest (Optional)
    - Build Docker Image and Push to ACR
    - Deployment to VM

<div style="page-break-after: always;"></div>

---

# Part 6: Backend, Ingress & Networking Architecture

[▲ Back to Table of Contents](#-table-of-contents)

## API Gateways

-

## Reverse Proxy (Ingress Layer)

- Serves as a protection for the API server (or any servers in general).

- Purpose:
  - Catch traffic on port 80
  - Check if request is valid
  - Terminates the SSL/TLS encryption (HTTP)
  - Forwards traffic within docker's internal network to the dedicated API gateway.
- Reverse proxies typically limits required ports of access under HTTP/HTTPS ports (80, 443), which is the universal standard for web traffic.
  - This is to give users a clean url (no `https://example.com:8080`).
- Also for security purposes, it lessens the way a potential attacker could access the servers by hiding the actual IP address of the website and web servers.
- Commonly utilizes NGINX

## NGINX

- Commonly utilizes nginx as the following:
  - Web Server (HTTP Request -> HTTP Response)
  - Proxy Server - Used for:
    - Load Balancing (One NGINX Server acts as a proxy server to distribute request to the rest of the servers.)
    - Caching (Instead of creating multiple fetch request within a database, such as a static article, a proxy server would request it ones and stores it temporarily for cases of multiple requests.)
    - Reverse Proxy (Serves as the only entry point for your servers by setting the default HTTP and HTTPS ports.)
    - Encrypted Communication (Accept encrypted traffic, deny non encrypted requests) Terminates the SSL/TLS encryption (HTTP)
    - Compression (Compresess request with large files included (such as videos) to lessen bandwidth usage and improve load times.)
    - Segmentation (Send responses in chunks, usually in video streaming.)
  - Modify configuration using `nginx.conf` file.

## Microservices Architecture

-

## SSL/TLS Certificates

### Why Does the Browser Say "Not Secure" on `https://localhost`?

When testing `https://localhost` in the browser, you will see a red lock or warning:

> **"Not secure - Your connection to this site is not secure"** (`NET::ERR_CERT_AUTHORITY_INVALID`)

This is completely normal and expected when using **self-signed certificates**.

---

### The Fundamental Rule: Encryption vs. Identity (Authentication)

A common misconception is that "Not Secure" means the connection is unencrypted. **It is not!**

| Concept                     | What It Means                                                                                   | Is It Working on `https://localhost`? |
| :-------------------------- | :---------------------------------------------------------------------------------------------- | :------------------------------------ |
| **1. Encryption (Privacy)** | Scrambles data so nobody sniffing Wi-Fi/network can read your traffic (uses RSA-2048, AES-256). | **YES (100% Active)**                 |
| **2. Identity (Trust)**     | Proves the server actually belongs to the person claiming to own it.                            | **NO (Self-Signed)**                  |

---

### How Browsers Check Certificates: The Trust Chain

1. Every operating system (Windows, macOS) and browser comes with a built-in list of **Trusted Root Certification Authorities** (e.g., DigiCert, Let's Encrypt, Google Trust Services, Sectigo).
2. When you connect to `https://google.com`, Chrome looks at Google's certificate, sees it was signed by a trusted CA on its pre-approved list, and displays a normal lock.
3. When you connect to `https://localhost` with our self-signed certificate, NGINX presents a certificate signed by **itself** (not a trusted CA).
4. Chrome does not know who created this certificate, so it warns the user:
   > _"I can encrypt the traffic, but I cannot guarantee who owns this server."_

---

### Local Dev vs. Real Production

- **Why we use self-signed certificates locally & on raw cloud IPs:**
  - Certificate Authorities (like Let's Encrypt) **only issue certificates to real, registered domain names** (e.g., `maas-api.com`). They will **never** issue a certificate for `localhost` or a raw IP address (`https://20.198.42.15`).
  - Therefore, self-signed certificates are the universal industry standard for local development, Docker environments, and raw IP testing.
- **How production makes it "Secure" (Green / Normal Lock):**
  1. Point a registered domain name (e.g. `api.maas.com`) to the Azure VM's public IP.
  2. Use **Let's Encrypt (Certbot)**, **Cloudflare**, or **Azure Key Vault** to issue a certificate signed by a recognized Certificate Authority.
  3. The browser verifies the CA signature, recognizes the authority, and removes the "Not Secure" warning.

---

# Part 7: Virtual Machine Deployment & Host Automation

[▲ Back to Table of Contents](#-table-of-contents)

## Cloud-Init & VM Provisioning

### What is Cloud-Init and Custom Data in Azure?

- `cloud-init` is a multi distribution method (some sort of automation tool) that runs on first boot to configure and customize a VM. ([cloud-init docs](https://docs.cloud-init.io/en/latest/index.html))
- It supports a variety of configuration options, including setting hostnames, default users, SSH keys, network configs, and running custom scripts.

- `custom-data` is a mechanism in Azure wherein you can pass custom configuration data (bash scripts or cloud-config yaml) to a VM during provisioning.
- When custom-data fails to execute, Azure does not notify you nor Terraform would not receive a failure notification.
- When custom-data is modified, terraform considers this as a new resource and will delete the old VM and recreate it with the updated `custom-data`.

### VM Boot Lifecycle & Execution Order

- Kernel Boot: Hardware and kernel initialization.
- `Local | cloud-init-local`: Identifies cloud provider datasource. Runs before networking is up.
- `Network | cloud-init (init)`: Networking comes up. Fetches metadata ad SSH keys.
- `Config | cloud-config`: Runs configuration scripts (user creation, package repos).
- `Final | cloud-final`: Where custom data is executed. Runs late in the boot process once networking is live and system services have initialized.

### Troubleshooting Cloud-Init Scripts (`/var/log/cloud-init-output.log`)

- When the script provided within `custom-data` fails to execute, Azure does not notify you nor Terraform would not receive a failure notification.

- To verify what actually happened, check the logs within the VM:

  - `cat /var/log/cloud-init-output.log` : Shows the full output of all commands run by the `custom-data` script.
  - `cat /var/log/cloud-init.log` : SHows the cloud-init system logs (steps, timings, errors).
  - `cloud-init status --long` : Shows the status of cloud-init, including any errors or warnings.

---

## VM Container Registry Access (ACR & Managed Identity)

### Private Container Registries (ACR) vs. Docker Hub

- **Docker Hub** is similar to GitHub.
  - Public by default. Images can be pulled publicly.
  - Images travel across the public interet.
  - Static usernames, passwords, and personal access tokens.
- **ACR** is similar to Docker Hub, but it is private by default.
  - ACR images are not publicly accessible.
  - Traffic stays within the Azure network only.
  - Integrated directly with Microsoft Entra ID (RBAC) & Managed Identity.

### The `AcrPull` Role & RBAC Configuration

- The `AcrPull` role is used to grant pull access (read-only access) to ACR images.
  - It is assigned to users or groups via RBAC.
- The `AcrPush` role is used to grant upload permissions (write access) to ACR images.
  - Used by CI/CD pipelines such as GitHub Actions.

#### Why Least Privilege Matters:

- When an attacker gains access to a system with admin/owner or `AcrPush` permissions, they can upload malicious images to ACR, inject malware, or delete the image entirely.

### Passwordless Pull via Managed Identity (`az acr login --identity`)

- Traditionally, `az acr login` requires a username and password or personal access token `docker login -u <username> -p <password>`.
- But this method is risky because passwords can be leaked within shell histories, .bash_history, config files, or logs.
- Using System Assigned Managed Identity, you can use a service principal or user-assigned managed identity to authenticate without a password.
  - `az acr login --identity` uses the system-assigned managed identity to authenticate.

---

## Reliable Deployments with systemd

### Linux `systemd` Init System (`systemctl`)

- The first process started by the linux kernel (PID 1).
- Responsible for managing system startup, background services, and the entire lifecycle. (init system and service manager)
- Every other services running within the system (SSH server, Docker daemon, networking, etc.) is a child process of the `systemd` init system.
- If a service crashes or stops, `systemd` will automatically restart it.
- When a machine boots up or shuts down, `systemd` will manage which services would start, wait, and shut down gracefully.

### Managing Docker Compose with Custom `.service` Unit Files

- Whenever a VM boots up or shuts down, and an existing container was started manually using `docker compose up`, `systemd` will not automatically restart it as it is not managed by `systemd`, unlike other services.
- To hand over the control of a container to `systemd`, you can use a custom `.service` unit file.
- You can create a custom `.service` unit file to define how `systemd` should manage the container.

**Sample `.service` syntax (`/etc/systemd/system/maas.service`):**

```ini
[Unit] # Dependency & Order Management Section
Description=MaaS Docker Compose Service
Requires=docker.service # Does not start app/service until docker is running. Sets a hard dependency to docker.
After=docker.service # Only start the app/service after confirming docker is fully initialized and listening.

[Service] # Execution Mechanics
Type=oneshot # Tells systemd that the service should be treated as a one-shot job, not a persistent service. It is just a command that runs the containers and exits back to the terminal, unlike a web server that stays running in the foreground.
RemainAfterExit=yes # Consider the service as running even after the command exits, so systemd does not restart it automatically.
WorkingDirectory=/home/azureuser/Maas # The directory where the Docker Compose files are located.
ExecStartPre=/usr/bin/az acr login --name acrmaascluster --identity # Command that must succeed before starting the service. Refresh the managed identity login to ACR.
ExecStart=/usr/bin/docker compose pull # Runs the deployment. Pull the latest Docker images from the ACR registry.
ExecStart=/usr/bin/docker compose up -d # Start the Docker containers in detached mode.
ExecStop=/usr/bin/docker compose down # When the VM shuts down or a manual stop command is made, stop the Docker containers.

[Install] # Boot Hook
WantedBy=multi-user.target # The service will be started once the dedicated runlevel is reached. In this case, the runlevel is `multi-user.target`, which is the default runlevel for a standard Linux system wherein the networking is up, the VM is accessible through SSH, and background daemons are running.
```

### Commands for Running and Diagnosing Services

- `sudo systemctl start <service>` # Start the service right now in the current session.
- `sudo systemctl enable <service>` # Enable the service to start automatically on boot.
- `sudo systemctl restart <service>` # Restart the service.
- `sudo systemctl stop <service>` # Stop the service.
- `sudo systemctl status <service>` # Check the status of the service.
- `sudo journalctl -u <service> -f` # View the live logs for the service.

---

## Continuous Deployment (CD) Pipelines to VM

### GitHub Actions to VM Deployment Overview

### Strategy A: SSH/SCP Push Deployment (Appleboy Action & Port 22)

- This strategy uses a job to SSH into the VM and restarting the service.
- Utilizes the `appleboy/ssh-action` to execute SSH commands.
- A script is provided within the same job block to restart the service.

### Strategy B: Self-Hosted GitHub Runners (Inbound Portless Architecture)

- This method includes installing GitHub's runner software directly on the VM as a service.
- The runner then makes an outbound HTTPS request to GitHub's API to fetch jobs.

### Security Considerations: SSH Open Ports vs. Runner Agents

| Dimension                             | SSH Push (`appleboy/ssh-action`)                                                               | Runner Agent (Self-Hosted Runner)                                             |
| :------------------------------------ | :--------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------- |
| **Communication Direction**           | **Inbound (Push):** GitHub Actions initiates connection to VM                                  | **Outbound (Pull):** Runner daemon on VM polls GitHub via HTTPS               |
| **Inbound Ports Required**            | **Port 22 (SSH)** must be open to the internet or GitHub IP ranges                             | **Zero inbound ports** needed (Port 22 can be completely closed in NSG)       |
| **Outbound Requirements**             | Standard outbound rules                                                                        | Outbound **HTTPS (Port 443)** to GitHub APIs                                  |
| **Network Exposure & Attack Surface** | **High:** Vulnerable to public IP port scans, brute-force SSH attacks, and SSH daemon exploits | **Low:** VM stays completely isolated behind private subnets and firewalls    |
| **Credential Management**             | Private SSH Key must be stored in GitHub Secrets                                               | No long-lived SSH private keys; uses short-lived tokens & VM Managed Identity |

<div style="page-break-after: always;"></div>

---

# Part 8: Azure Observability (Monitor & Log Analytics)

[▲ Back to Table of Contents](#-table-of-contents)

## The Concept of Centralized Logging

- Traditional VM administration (viewing logs stored within `/var/log/app.log`) is an anti-pattern for cloud.
  - If a VM runs out of disk space due to large unrotated log files, it can become unresponsive or crash.
  - If VMs are auto-scaled, the instance will be terminated and replaced, potentially losing log data.
- In cloud environments, logs should be centralized and ingested from all sources.

### Logs vs. Metrics

- **Logs** are detailed, event driven, structured data about events that occur within an application or system.
  - User login failed
  - Database connection error
  - Stack traces
- **Metrics** are numerical values that are sampled at regular intervals and represent the state of a system or application.
  - CPU Usage
  - Memory Usage
  - Network Traffic
  - Requests per Second

### Azure Log Analytics Workspace (LAW)

- A LAW is a centralized repository for logs and metrics from various sources.
- It is a dedicated resource for storing application logs and metrics. The data is then used in Azure Monitor and other tools for monitoring and alerting.
- It is responsible for ingesting, storing, and analyzing log data from various sources.

#### Why Separate Logs and have a dedicated data store?

- **Tamper Resistance**: Logs are stored in a dedicated data store that is not accessible to the application. When an attacker gains access to the application, they cannot tamper with or delete the logs.
- **Resource Efficiency**: Running heavy queries (grep, awk) on long lines of raw log data can be resource-intensive for the VM. By utilizing a dedicated data store, heavy queries can be offloaded to a completely separate system.
- **Centralized Logging**: Logs are collected from multiple VM instances and stored in a centralized location, making it easier to create join queries and analyze log data from multiple resources at once.
- **Cost Efficiency**: Storing logs in a dedicated data store can be more cost-effective than running heavy queries on raw log data stored in the VM's own disk.

## Ingesting Docker Logs

- By default, Docker logs are stored in the VM's own disk (`/var/lib/docker/containers/<container_id>/<container_id>-json.log`).

### Local -> Log Analytics Workspace

- To import Docker logs into a Log Analytics Workspace, there are several options available:

  - **Using `Azure Monitor Agent`**
    - The host VM is responsible for collecting and sending the telemetry to the Log Analytics Workspace.
    - Azure Monitor Agent runs as a background service within the `systemd` daemon.
    - **Log Ingestion Flow:**

      ```mermaid
      flowchart LR
          A["Container (stdout/stderr)"] --> B["Host Syslog (docker-compose.yml)"]
          B --> D["Azure Monitor Agent (AMA)"]
          DCR["Data Collection Rule (DCR)"] -.->|"Instructs & Filters"| D
          D --> E["Log Analytics Workspace (LAW)"]
      ```

      1. Container will emit `stdout`/`stderr`
      2. Container stack will be configured to send logs within the host's syslog through the `docker-compose.yml` file
      3. Data Collection Rule (DCR) defines what to collect, in-flight transformations, and the target workspace
      4. Azure Monitor Agent (AMA) reads syslog data, applies DCR filtering, and ships logs to the Log Analytics Workspace using the VM's Managed Identity

  - **Using a dedicated log shipper**
    - Bypass the native logging agents and use a dedicated log shipper (Vector, Fluent Bit) to call Azure's REST API to send logs to the Log Analytics Workspace.
    - **Log Ingestion Flow:**

      ```mermaid
      flowchart LR
          A["Container (stdout/stderr)"] --> B["Log Shipper (Vector / Fluent Bit)"]
          B -->|Direct HTTP POST via Azure REST API| C["Log Analytics Workspace (LAW)"]
      ```

      1. Container will emit `stdout`/`stderr`
      2. Container stack will be configured to send logs to the log shipper
      3. Chosen log shipper will send logs to the Log Analytics Workspace by making direct HTTP POST request to Azure
      4. Log shipper will authenticate by having its own Service Principal

## Kusto Query Language (KQL)

- Similar concept to SQL, but more focused on querying log data
- Pipeline based language similar to Unix shell commands/Bash

```kql
Syslog
| where TimeGenerated > ago(24h)
| where SeverityLevel == "error"
| project TimeGenerated, ProcessName, SyslogMessage
| order by TimeGenerated desc
| take 50
```

### Core KQL Operators

- `where`: filters rows based on a condition:
  - `==`: exact equality match
  - `has`: fast whole-word/token match using the **Inverted Term Index** (O(1) index lookup)
  - `contains`: slow arbitrary substring scan (case-insensitive **brute-force table scan**)
- `project`: selects specific columns to include in the output
- `extend`: creates new columns within the output based on existing ones
- `summarize`: aggregates data based on a grouping key (similar to SQL GROUP BY, AVG, SUM)
- `take / limit`: limits the number of rows returned

### KQL Aggregations

- `summarize`: aggregates data based on a grouping key (similar to SQL GROUP BY, AVG, SUM)
  - `count`: counts the number of rows in the output
  - `avg`: calculates the average of a numeric column
  - `sum`: calculates the sum of a numeric column
- `bin()`: bins (groups) data into time intervals (e.g. `bin(TimeGenerated, 1h)`)
- `render timechart`: renders a time chart of the data (line graph) in the Azure portal

```kql
Syslog
| where TimeGenerated > ago(6h)
| where SyslogMessage has "error"
| summarize ErrorCount = count() by bin(TimeGenerated, 15m), ProcessName
| render timechart
```

## Application Insights
- When an action is done within the backend microservice architecture, you would be able to see the general logs such as HTTP 200 OK, 404 Not Found, 500 Internal Server Error with accompanying time to execute the request.
  - The problem: what caused the 12 second delay?
  - Plain centralized logs can tell you what individual services saw, but they do not show the **chain of custody** across services.

- Application Insights is Azure's Application Performance Monitoring (APM) service that provides telemetry data on your applications.
- Its data is also stored within Log Analytics Workspaces (LAW), but in specialized schema tables:
  - `AppRequests`: Inbound HTTP requests received by a service (duration, status code).
  - `AppDependencies`: Outbound calls made by a service (calls to Postgres, Redis, or other HTTP microservices).
  - `AppExceptions`: Unhandled exceptions and stack traces.
  - `AppTraces`: Custom log messages emitted by your application logger.

### Distributed Tracing & W3C Trace Context
- Distributed tracing is the process of tracking a request as it moves through a distributed system.
```trace
User Click ──> [API Gateway] ──HTTP──> [Billing Service] ──SQL──> [PostgreSQL]
```
- Whenever a request is made within the system, a trace context is attached to the request.
- The trace context is propagated across services using W3C Trace Context headers.
  - 1. When a request is received, the API Gateway generates a unique random ID called the trace ID.
  - 2. When the gateway makes a request to the next service, the trace ID is propagated to the downstream services via the `traceparent` header:
    ```http
    GET /billing/charge HTTP/1.1
    Host: billing-service
    traceparent: 00-abc123456789-span1-01
    ```
  - 3. When the next service receives the request, it extracts the `traceparent` header and uses it to create a new trace context (e.g. when calling the database, it tags the query with the trace ID so that the trace context is preserved across the call).

### Trace Vocabulary
- **Trace**: A single request that moves through a distributed system, identified by a unique trace ID.
- **Span**: A single operation within a trace, such as a database query or an HTTP request.
- **Trace Context**: The data associated with a trace, including the trace ID and span information.
- **Application Map**: A visual representation of the distributed system, showing the relationships between services and their trace data. Azure can automatically create a visual diagram with arrows that shows your architecture and how may milliseconds each arrow took.

### Trace Context Installation Approach
- **SDK Approach**: Use `azure-monitor-opentelemetry` and initialize within your service code.
  - Full control and fully customizable.
  - Requires code changes and image redeployment.

- **Auto-Instrumentation**: Use `opentelemetry-instrument` to automatically instrument your service code without any changes.
  - Zero code changes in exchange for less control and customization.

<div style="page-break-after: always;"></div>

---

# Part 9: Notes to Self & Career Roadmap

[▲ Back to Table of Contents](#-table-of-contents)

## Refresh on Networking Concepts ( bro you know all of these from 3rd year)

- [x] CIDR Notation
- [x] IP Subnetting
- [x] OSI Layer
  - [x] Layer 4: TCP vs UDP
  - [x] Layer 7: HTTP, HTTPS, WebSockets
- [/] Network Address Translation
- [x] DNS
- [x] Routing

## Cloud Concepts

- [x] Infrastructure as Code (IaC)
- [x] State Files
- [ ] Shared Responsibility Model
- [x] Virtual Machines (IaaS)
- [ ] App Services (PaaS)
- [x] Container Registries (ACR)
- [ ] Kubernetes Services (AKS)
- [x] Virtual Networks (VNet)
- [x] Subnets
- [x] Network Security Groups (NSG)
- [x] Network Interfaces (NIC)
- [x] Public IPs
- [ ] Load Balancers
- [ ] Application Gateways
- [ ] Managed Disks
- [x] Blob Storage
- [ ] Managed Databases (SQL / PostgreSQL)
- [x] Identity & Access Management (IAM)
- [x] Role-Based Access Control (RBAC)
- [x] Azure Entra ID
- [x] Azure Key Vault
- [x] Managed Identities
- [x] Log Analytics / Azure Monitor

## Linux Commands & Concepts

- [x] Package Management (APT)
- [x] GPG Keys & Keyrings
- [x] Sources List (`/etc/apt/sources.list.d/`)
- [x] File Permissions (`chmod`)
- [x] Permission Bits (`0755`, `a+r`)
- [x] File Ownership (`chown`)
- [x] User & Group Management (`usermod`)
- [x] Shell Redirection (`|`, `>`, `>>`)
- [x] Environment Variables
- [x] curl
- [x] tee
- [x] dpkg
- [x] lsb_release

## Additional DevOps & Backend Concepts

- [x] CI/CD Pipelines
- [x] GitHub Actions Workflows (`.yml`)
- [x] Containerization (Docker)
- [x] Container Orchestration
- [x] Observability (Logging and Monitoring)
- [/] Git Flow (rebase, cherry-pick)
- [x] Reverse Proxies (Nginx, Caddy)
- [x] SSL/TLS Certificates
- [x] Microservices Architecture
- [x] API Gateways
- [x] Secret Management

## Career Advice & Transition Suggestions

To transition from backend to DevOps/Cloud in the long run:

1. Containerize Existing Projects: Add a Dockerfile and docker-compose.yml to your
   Coffeetory POS application. Document this in the repository. Containerization is
   the bedrock of modern DevOps.
2. Add Observability / Telemetry: For KidSync or Coffeetory, set up basic telemetry.
   Even simple setups like exporting application logs to a CloudWatch/Azure Log
   Analytics workspace or hooking up Prometheus/Grafana will show you understand
   operations.
3. Build a Multi-Tier Cloud Project: Create a small, new deployment using Terraform.
   For example, deploy a containerized backend on AWS ECS or Azure Container Apps,
   behind a load balancer, talking to a managed cloud database.
4. Certifications (Optional but helpful for resume scanning): AWS Certified Cloud
   Practitioner / Solutions Architect Associate, or Microsoft Azure Fundamentals (AZ-

900) / Administrator (AZ-104).
