# Practical Guide: Setting Up Azure Key Vault

This guide walks through creating a Key Vault using Terraform, assigning RBAC, and storing your first secret.

## Step 1: Add Key Vault to Terraform
In `infra/terraform/main.tf`, define the Key Vault:

```hcl
data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "maas_kv" {
  name                        = "kv-maas-cluster-1234" # Must be globally unique
  location                    = azurerm_resource_group.maas_rg.location
  resource_group_name         = azurerm_resource_group.maas_rg.name
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  sku_name                    = "standard"
  enable_rbac_authorization   = true # Use RBAC instead of Access Policies
}
```

## Step 2: Assign Yourself the Secrets Officer Role
To create secrets via the Azure Portal or CLI, you (and your Terraform Service Principal) need the "Key Vault Secrets Officer" role.

```hcl
resource "azurerm_role_assignment" "tf_kv_officer" {
  scope                = azurerm_key_vault.maas_kv.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}
```

## Step 3: Create a Secret via Terraform
Now that you have permissions, you can create a secret.

```hcl
resource "azurerm_key_vault_secret" "jwt_secret" {
  name         = "jwt-secret"
  value        = "your-super-secret-jwt-key" # In real life, use a random_password resource!
  key_vault_id = azurerm_key_vault.maas_kv.id
  
  depends_on = [azurerm_role_assignment.tf_kv_officer]
}
```

## Step 4: Grant the VM Access to Read Secrets
If you want the FastAPI app on the VM to read this secret, you assign the VM a Managed Identity, and grant that identity the "Key Vault Secrets User" role.

```hcl
resource "azurerm_role_assignment" "vm_kv_reader" {
  scope                = azurerm_key_vault.maas_kv.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_linux_virtual_machine.maas_vm.identity[0].principal_id
}
```
*(Note: You must add an `identity { type = "SystemAssigned" }` block to your VM definition first!)*
