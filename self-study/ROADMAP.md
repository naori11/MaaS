# DevOps & Networking Learning Roadmap

---

## Phase 1: Core Networking & Subnetting Re-Activation
> **Goal:** Rebuild core networking fundamentals, subnetting calculations, and Cisco Packet Tracer confidence before moving to system administration.

### Action Tasks
- [ ] **IP Addressing & Subnetting Reset**
  - [ ] Re-learn CIDR notation (`/24`, `/28`, `/16`).
  - [ ] Practice calculating Network ID, Broadcast Address, First Usable IP, Last Usable IP, and Subnet Mask manually.
  - [ ] Complete subnetting drills (e.g., dividing `192.168.1.0/24` into 4 equal subnets of `/26`).
- [ ] **Packet Tracer Micro-Lab #1: Basic LAN & Subnetting**
  - [ ] Set up 2 separate subnets using a single router (e.g., Subnet A: `10.0.1.0/24`, Subnet B: `10.0.2.0/24`).
  - [ ] Connect PCs to switches, assign static IPs, configure default gateways, and verify `ping` end-to-end.
- [ ] **Packet Tracer Micro-Lab #2: NAT & Routing**
  - [ ] Configure static/dynamic routing between 2 routers.
  - [ ] Implement NAT (Network Address Translation) to map private IPs to public IP addresses.
- [ ] **OSI Model Deep-Dive**
  - [ ] **Layer 4 (Transport):** Contrast TCP (three-way handshake, stateful) vs. UDP (stateless, fast).
  - [ ] **Layer 7 (Application):** Review HTTP/HTTPS request headers, response codes, and WebSockets.

---

## Phase 2: Linux Systems & Administration (Ubuntu Native)
> **Goal:** Get comfortable navigating, managing permissions, and inspecting system state directly inside your Ubuntu installation.

### Action Tasks
- [ ] **Directory Navigation & File Operations**
  - [ ] Practice essential file commands: `ls -la`, `cd`, `mkdir -p`, `cp -r`, `mv`, `rm -rf`.
  - [ ] Master terminal text processing: `cat`, `less`, `head`, `tail -f`, `grep`, and `find`.
  - [ ] Use shell redirection operators (`|`, `>`, `>>`, `tee`) to filter outputs and log to files.
- [ ] **Permissions & Ownership**
  - [ ] Practice `chmod` in both absolute mode (`chmod 755`) and symbolic mode (`chmod +x script.sh`).
  - [ ] Practice changing file/directory ownership using `chown user:group filename`.
  - [ ] Practice user privileges management (`useradd`, `usermod -aG sudo $USER`).
- [ ] **Package Management & System Repositories**
  - [ ] Update package index and upgrade system (`sudo apt update && sudo apt upgrade`).
  - [ ] Inspect source lists under `/etc/apt/sources.list` and `/etc/apt/sources.list.d/`.
  - [ ] Practice adding custom GPG keys and APT repositories (e.g., Docker repository setup).
- [ ] **Environment Variables & Shell Configuration**
  - [ ] Inspect active variables (`env`, `printenv`, `echo $PATH`).
  - [ ] Set temporary variables (`export VAR=value`) vs. permanent ones inside `~/.bashrc`.
- [ ] **System & Process Monitoring**
  - [ ] Practice process management (`ps aux`, `top`, `htop`, `kill -9 <PID>`).
  - [ ] Manage system services via `systemctl` (`status`, `start`, `stop`, `enable`, `restart`).

---

## Phase 3: Containerization & Edge Networking
> **Goal:** Connect Linux shell skills and Layer 4/7 networking directly to your backend microservices architecture.

### Action Tasks
- [ ] **Linux Network Inspection Commands**
  - [ ] Practice `curl -Iv <url>` to inspect HTTP response headers and SSL handshakes.
  - [ ] Run `ping` and `traceroute` for latency and path tracking.
  - [ ] Check open listening ports using `ss -tuln` or `netstat -tuln`.
  - [ ] Perform DNS lookup diagnostics using `dig` or `nslookup`.
- [ ] **Docker Internal Networking & Service Discovery**
  - [ ] Understand Docker bridge networks and container isolation.
  - [ ] Review DNS service discovery in `docker-compose.yml` (`http://identity:8000`).
  - [ ] Clarify port mapping concepts (`-p 8080:80`).
- [ ] **NGINX Reverse Proxy & SSL Termination**
  - [ ] Review HTTP (Port 80) to HTTPS (Port 443) redirection rules.
  - [ ] Configure `proxy_pass` directives to route incoming traffic to internal services.
  - [ ] Understand SSL/TLS handshake termination at the edge proxy layer.

---

## Phase 4: Cloud Virtual Networking & Infrastructure as Code
> **Goal:** Map your Packet Tracer, Linux, and edge networking knowledge to public cloud infrastructure using Terraform.

### Action Tasks
- [ ] **Azure Networking Concepts**
  - [ ] Map Virtual Networks (VNets) to private LAN concepts.
  - [ ] Segment a VNet (`10.0.0.0/16`) into public (`10.0.1.0/24`) and private (`10.0.2.0/24`) subnets.
  - [ ] Configure Network Security Groups (NSGs) as cloud firewalls restricting inbound/outbound ports.
  - [ ] Understand virtual Network Interface Cards (NICs) and Public IP attachments.
- [ ] **Terraform IaC Review**
  - [ ] Review `azurerm_virtual_network`, `azurerm_subnet`, and `azurerm_network_security_group` declarations in code.
- [ ] **Terraform Remote State Backend**
  - [ ] Understand why local `terraform.tfstate` files pose production and deployment risks.
  - [ ] Configure an Azure Blob Storage backend (`backend "azurerm"`) for state locking and shared management.