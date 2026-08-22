# Managing Dependencies (python based backend)

## For python based APIs:

- To create the requirements.txt file, use
  - `python -m venv venv` (create a virtual environment)
  - `pip install` the necessary dependencies
  - `pip freeze > requirements.txt`
  - or to automatically fetch the necessary dependencies (static code analysis), use `pipreqs` | `pip install pipreqs` | `pipreqs . --force`

- To separate test file dependencies (for github actions unit test)
  - create a separate `requirements-dev.txt` file
  - put dependencies mainly for testing only (pytest, httpx)
  - standard dependencies for testing in python is pytest and httpx

# Creating Dockerfiles

- Dockerfile notes are commented under each dockerfile within this project.
- Always create a `.dockerignore` file. Put the files unnecessary for the deployed state such as unit tests, python caches, venv, `.git` and `.gitignore` files.

## Testing Dockerfiles (Buidling and Running docker images)

- `docker build -t 'image_name':'tag' .` | command for building the image based on dockerfile. Must run within the directory of the app.
- `docker run -p 'host_port':'container_port' 'image_name'` | command for running the image. Add `-d` before image name to detach terminal.
- `docker ps` / `docker ps -a` | command to list running/dead or exited containers
- `docker stop 'container_id'` | shuts down a running container
- `docker rm 'container_id'` | removes the container build
- `docker system prune` | removes every image/build that are unused
- `docker exec -it 'container_id' /bin/sh` or `/bin/bash` | opens a live terminal within the container

# Docker Compose

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

# Terraform (IaC - Infrastructure as Code)

- Made after creating the initial services cluster (the API.)
- `terraform init` | command for preparing terraform directory (`.terraform`). Donwloads necessary provider plugins (defined under `terraform/required_providers` block)
- `terraform plan` | command that shows terraform execution plan to the actual infrastructure platform
- `terraform apply` | applies the IaC by spinning up the resources defined within the code along with its configurations
- `terraform destroy` | removes everything that is defined within the terraform configuration
- `terraform fmt` | formats your code to make it more clean

# Terraform State Management

- Terraform state (`.tfstate`) file is a JSON file that tracks the resources created by Terraform the last time the `terraform apply` command was run.
- It is used by Terraform to keep track of the resources (as a lookup table) it has created and to ensure that the infrastructure matches the desired state defined in the code.


**Scenario 1:** If you manually delete a Virtual Network in the Azure Portal, but don't touch your Terraform code or state file, what happens the next time you run `terraform plan`? Why?

- Terraform will perform a background refresh by checking the `.tfstate` file for the existing resources, then calls Azure API for each resource to verify its existence.
- Then terraform will detect that the resource no longer exists.
- If the resource is still within the `.tf` file, the next time that `terraform apply` is run, it will attempt to create the resource again.

**Scenario 2:** If you delete your local `terraform.tfstate` file, but the Azure resources still exist, what happens the next time you run `terraform apply`?

- Terraform will not have any state to compare against, so it will treat the resources as not existing and attempt to create them again.
- But since all of the resources still exist in Azure, and there is no lookup table to compare with, Azure would return rejected requests. 
- It does not recreate the state file, so the next time you run `terraform apply`, it will still treat the resources as not existing. The only way to fix this is to either delete the resources from Azure or recreate the state file by importing them into Terraform using `terraform import`.

**If Developer A and Developer B both run `terraform apply` from their own laptops at the exact same time using local state, what is the risk to the Azure environment?**
- Multiple API calls to create resources will be sent and could cause conflicts, duplicate resources, and broken tfstate files for both ends.

**Why can’t you just commit `terraform.tfstate` to Git to solve the collaboration problem? (Hint: There are two major reasons—one relates to merging, the other to security).**
- Merge conflicts, and tfstate files contains secrets such as ssh keys, admin passwords, API tokens, etc. On which, everything is stored as plaintext, and Azure Blob storage is the one encrypthing it.

**How does Terraform provision the resource needed for the remote state file if it does not exist yet?**
- You provision it manually using the Azure portal or CLI.
- Through bootsrapping. Create a separate Terraform configuration file first in a separate directory which provisions the storage account and container for the remote state file. Then you can run `terraform init` in the main directory to use the remote state file.

**Key CLI commands**
- `terraform state list`: Lists all resources in the state file.
- `terraform state show <resource>`: Shows the details of a specific resource in the state file.
- `terraform import <resource> <id>`: Imports an existing resource from Azure into the state file in cases of people adding resources manually.
- `terraform state rm <resource>`: Removes a resource from the state file without deleting it from Azure.
- `terraform state mv <old_resource> <new_resource>`: Renames a resource in the state file.

# Azure Blob
- Azure Blob Storage is a service that allows you to store unstructured data such as logs, backups, and media files.
- Has a Blob Lease feature that allows you to lock a file (a blob) when it is being used by a resource, such as terraform's state files to prevent other resources from modifying it until it is done.

# SSH Keygen 

- `ssh-keygen -t rsa -b 4096 -C "sample@email.com"` | command for creating an SSH key pair for your local machine
- When command is run, it generates an `id_rsa.pub` (public key) and `id_rsa` (private key)
- Layman concept: `id_rsa.pub` is the lock and `id_rsa` is your key to the lock. You provide the lock in a VM instance. 
- When you try to connect via SSH, your local machine uses the key to verify the signature based on the lock provided. Once verified, you will be given access to the VM without entering a password.

# Azure Container Registry (ACR)

- Basically storage of Docker Images to be deployed within the VM
- Docker images are built within Github Actions (CI/CD) and pushed within ACR
- `admin_enabled` is set as true to have a username and password credentials to put within Github Actions secrets

# GitHub Actions

- Ideal pipelines for development:
  - Pull Requests:
    - Linting and Formatting (Did the developer follow the team's style guide? (e.g., no messy spacing, correct variable casing). If it fails, block the PR.)
    - Unit Testing (Unit tests made for each service)
    - Security Check (Are there any hardcoded passwords or glaring SQL injection vulnerabilities?)
  - Commit to Prod/Main Branch
    - Retest (Optional)
    - Build Docker Image and Push to ACR
    - Deployment to VM

# Backend Concepts

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

# Notes to Self

## Refresh on Networking Concepts ( bro you know all of these from 3rd year)

- [x] CIDR Notation
- [ ] IP Subnetting
- [ ] OSI Layer
  - [ ] Layer 4: TCP vs UDP
  - [ ] Layer 7: HTTP, HTTPS, WebSockets
- [ ] Network Address Translation
- [ ] DNS
- [ ] Routing

## Cloud Concepts

- [x] Infrastructure as Code (IaC)
- [ ] State Files
- [ ] Shared Responsibility Model
- [x] Virtual Machines (IaaS)
- [ ] App Services (PaaS)
- [ ] Container Registries (ACR)
- [ ] Kubernetes Services (AKS)
- [ ] Virtual Networks (VNet)
- [ ] Subnets
- [ ] Network Security Groups (NSG)
- [ ] Network Interfaces (NIC)
- [ ] Public IPs
- [ ] Load Balancers
- [ ] Application Gateways
- [ ] Managed Disks
- [ ] Blob Storage
- [ ] Managed Databases (SQL / PostgreSQL)
- [ ] Identity & Access Management (IAM)
- [ ] Role-Based Access Control (RBAC)
- [ ] Azure Entra ID
- [ ] Azure Key Vault
- [ ] Managed Identities
- [ ] Log Analytics / Azure Monitor

## Linux Commands & Concepts

- [x] Package Management (APT)
- [ ] GPG Keys & Keyrings
- [ ] Sources List (`/etc/apt/sources.list.d/`)
- [x] File Permissions (`chmod`)
- [x] Permission Bits (`0755`, `a+r`)
- [x] File Ownership (`chown`)
- [x] User & Group Management (`usermod`)
- [ ] Shell Redirection (`|`, `>`, `>>`)
- [x] Environment Variables
- [ ] curl
- [ ] tee
- [ ] dpkg
- [ ] lsb_release

## Additional DevOps & Backend Concepts

- [x] CI/CD Pipelines
- [x] GitHub Actions Workflows (`.yml`)
- [x] Containerization (Docker)
- [ ] Container Orchestration
- [ ] Observability (Logging and Monitoring)
- [/] Git Flow (rebase, cherry-pick)
- [/] Reverse Proxies (Nginx, Caddy)
- [ ] SSL/TLS Certificates
- [ ] Microservices Architecture
- [x] API Gateways
- [ ] Secret Management

### Career Advice & Transition Suggestions

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
