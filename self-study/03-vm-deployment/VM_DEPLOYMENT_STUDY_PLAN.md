# Step 3: VM Deployment: Self-Study Plan

This module bridges the gap between running `docker-compose up` on your laptop and running it reliably on an Azure Virtual Machine as a production-like environment.

---

## Module 1: Cloud-Init & VM Provisioning
**Topics to Research:**
- What is `cloud-init` and `custom-data` in Azure?
- The VM boot sequence and when custom data scripts execute.
- Troubleshooting broken cloud-init scripts (`/var/log/cloud-init-output.log`).

**Check for Understanding:**
1. If you update the `custom_data` script in Terraform, does Terraform automatically reboot the VM and run the script again?
2. How do you verify if the Docker installation script ran successfully on a new Azure VM?

---

## Module 2: Accessing the Container Registry
**Topics to Research:**
- Private Container Registries (ACR) vs Docker Hub.
- The `AcrPull` RBAC role.
- How an Azure VM uses a System-Assigned Managed Identity to log into ACR without a password (`az acr login --identity`).

**Check for Understanding:**
1. Why is it better to use `az acr login --identity` on the VM rather than passing the ACR Admin Password to the VM?
2. If your VM can't pull an image, what two things should you check? (Hint: Networking and RBAC).

---

## Module 3: Reliable Deployments with systemd
**Topics to Research:**
- The Linux `systemd` init system (`systemctl start`, `systemctl enable`).
- Creating a custom `.service` file to manage `docker-compose`.
- Ensuring the app restarts automatically if the VM reboots.

**Check for Understanding:**
1. If you just SSH into the VM and run `docker-compose up -d`, what happens when the Azure infrastructure restarts the VM for patching?
2. How does a `systemd` service file guarantee the app stays alive?

---

## Module 4: CD (Continuous Deployment) Pipelines
**Topics to Research:**
- Deploying from GitHub Actions to a VM.
- Option A: SSH/SCP to copy files and execute commands.
- Option B: Self-hosted GitHub Runners on the VM.

**Check for Understanding:**
1. What are the security implications of opening Port 22 (SSH) to the entire internet for GitHub Actions?
2. How can a self-hosted runner bypass inbound NSG rules?
