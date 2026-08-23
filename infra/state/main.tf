# -----------------------------------------
# Bootstrap Infrastructure for Terraform State
# -----------------------------------------

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
  # Same as your main project, allowing Terraform to auto-register required providers
  skip_provider_registration = false
}

# 1. Create a dedicated Resource Group for the Terraform state
resource "azurerm_resource_group" "tfstate_rg" {
  name     = "rg-terraform-state"
  location = "eastasia"
}

# 2. Create the Storage Account
resource "azurerm_storage_account" "tfstate_sa" {
  name                     = "maastfstate1" # MUST BE GLOBALLY UNIQUE (Change this if it's taken)
  resource_group_name      = azurerm_resource_group.tfstate_rg.name
  location                 = azurerm_resource_group.tfstate_rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS" # Standard_LRS

  # Highly recommended for state files: This prevents you from accidentally
  # deleting the storage account if you ever run 'terraform destroy' in this folder.
  lifecycle {
    prevent_destroy = true
  }
}

# 3. Create the Blob Container inside the Storage Account
resource "azurerm_storage_container" "tfstate_container" {
  name                  = "tfstate"
  storage_account_name  = azurerm_storage_account.tfstate_sa.name
  container_access_type = "private" # Ensure the state file is not publicly readable
}
