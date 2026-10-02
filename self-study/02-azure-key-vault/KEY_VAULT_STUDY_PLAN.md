# Step 2: Azure Key Vault: Self-Study Plan

This module focuses on secure secret management, moving hardcoded configurations and passwords out of your code and environment variables into a secure, managed vault.

---

## Module 1: The Concept of a Key Vault
**Topics to Research:**
- What is Azure Key Vault? 
- The difference between Secrets, Keys, and Certificates.
- The principle of Least Privilege applied to secrets.

**Check for Understanding:**
1. Should you store a database password as a Secret, a Key, or a Certificate?
2. If your application code is open-sourced or leaked, why does having a Key Vault protect your database?

---

## Module 2: Key Vault Access Models
**Topics to Research:**
- Key Vault Access Policies vs. Azure RBAC for Key Vault data plane.
- The "Key Vault Secrets User" role.
- How a Virtual Machine (using a Managed Identity) authenticates to the Key Vault.

**Check for Understanding:**
1. If your VM needs to read a database connection string from Key Vault, what identity and RBAC role does it need?
2. Why is Azure RBAC the recommended modern approach over legacy Access Policies?

---

## Module 3: Key Vault Integration with Terraform
**Topics to Research:**
- Creating an `azurerm_key_vault` and `azurerm_key_vault_secret` in Terraform.
- Reading a secret dynamically in Terraform using a `data` block.
- The `depends_on` tricky relationship between Key Vault creation and RBAC assignment.

**Check for Understanding:**
1. If Terraform creates a Key Vault and a Secret in the same `apply`, why might it fail if the Service Principal running Terraform doesn't have the "Key Vault Secrets Officer" role?
2. Can Terraform read a secret from Key Vault without saving it in the `terraform.tfstate` plaintext? (Hint: The answer highlights why state security is crucial).

---

## Module 4: Injecting Secrets into the App
**Topics to Research:**
- Reading Key Vault secrets directly in Python/FastAPI using the `azure-identity` and `azure-keyvault-secrets` SDKs.
- Injecting secrets via environment variables during Docker deployment (e.g., pulling secrets before starting the compose stack).

**Check for Understanding:**
1. What is the benefit of having FastAPI fetch the secret directly from Key Vault vs. passing it in via `.env` file?
