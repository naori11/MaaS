# Terraform Remote State: Self-Study Plan

This is a structured, concept-driven study plan designed to bridge the gap between "writing Terraform tutorials" and "running Terraform in production." 

For each module, research the core concepts and ensure you can confidently answer the "Check for Understanding" questions before moving to the next module. Do not focus on writing implementation code until you understand the theory.

---

## Module 1: The Core Concept of Terraform State
Before moving state to the cloud, you must understand what state actually *is* and why Terraform needs it.

**Topics to Research:**
- The purpose of the `terraform.tfstate` file.
- The relationship between: **Desired Configuration** (your `.tf` files), **State** (what Terraform *thinks* exists), and **Real Infrastructure** (what actually exists in Azure).
- How Terraform uses state to map resource blocks (e.g., `azurerm_virtual_network.main`) to real-world cloud IDs.

**Check for Understanding:**
1. If you manually delete a Virtual Network in the Azure Portal, but don't touch your Terraform code or state file, what happens the next time you run `terraform plan`? Why?
2. If you delete your local `terraform.tfstate` file, but the Azure resources still exist, what happens the next time you run `terraform apply`? 

---

## Module 2: The Problems with Local State
Understand the pain points that make remote state a strict requirement for professional projects.

**Topics to Research:**
- Team collaboration and the "split-brain" state problem.
- Continuous Integration (CI/CD) environments (like GitHub Actions) and ephemeral filesystems.

**Check for Understanding:**
1. If Developer A and Developer B both run `terraform apply` from their own laptops at the exact same time using local state, what is the risk to the Azure environment?
2. Why can't you just commit `terraform.tfstate` to Git to solve the collaboration problem? (Hint: There are two major reasons—one relates to merging, the other to security).

---

## Module 3: Remote State & Azure Blob Storage
Learn how to offload the state file to Azure so it acts as a centralized source of truth.

**Topics to Research:**
- The Terraform `backend` block (specifically the `azurerm` backend).
- Why Azure Blob Storage is used (durability, versioning, access).
- The concept of "State Locking" (using Azure Storage blob leases).

**Check for Understanding:**
1. What does the `backend "azurerm" {}` configuration actually do to the `terraform init` process?
2. How does Terraform prevent Developer A and Developer B from applying changes simultaneously when using an Azure Blob backend? How does a "blob lease" work?

---

## Module 4: State Security and Sensitive Data
State files are dangerous if exposed. You must study how Terraform handles secrets.

**Topics to Research:**
- Plaintext secrets in the `.tfstate` file (e.g., database passwords, API keys).
- Azure Storage Account access keys vs. Role-Based Access Control (RBAC).
- Encrypting state at rest.

**Check for Understanding:**
1. If you pass a password into Terraform using an environment variable (`TF_VAR_password`), does that password end up inside the remote state file? If so, is it encrypted by Terraform?
2. Who should be allowed to read the Terraform state blob container in Azure?

---

## Module 5: The "Chicken and Egg" Bootstrapping Problem
You need an Azure Storage Account to hold your Terraform state. But you use Terraform to create Azure resources. How do you create the Storage Account that holds the state?

**Topics to Research:**
- The concept of "Bootstrapping" infrastructure.
- Multi-layered Terraform architectures (e.g., separating the foundational state infrastructure from the application infrastructure).

**Check for Understanding:**
1. Why is it a bad idea to define the Azure Storage Account that holds your state *inside* the same Terraform state file it is hosting?
2. What are the two common ways DevOps engineers create the initial Storage Account? (Hint: one involves a script, the other involves a separate, locally-stated Terraform directory).

---

## Module 6: State Manipulation and Recovery (The CLI Tools)
In the real world, state gets out of sync. You need to know how to fix it without destroying the cloud.

**Topics to Research:**
- `terraform state list` and `terraform state show`.
- `terraform import` (bringing existing, manually created cloud resources into Terraform's control).
- `terraform state rm` (telling Terraform to forget about a resource without actually deleting it from Azure).
- Configuration drift and `terraform refresh`.

**Check for Understanding:**
1. Your coworker manually created an Azure Postgres Database. How do you bring it under Terraform management without deleting and recreating it?
2. You want to rename a resource block in your `.tf` file from `azurerm_resource_group.old` to `azurerm_resource_group.new`. If you just change the text and run `apply`, Terraform will destroy the old group and create a new one. How do you update the state to prevent destruction?
