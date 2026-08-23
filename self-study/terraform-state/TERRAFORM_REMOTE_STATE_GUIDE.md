# Practical Guide: Setting Up Terraform Remote State

This guide walks through the practical application of moving your local Terraform state to a remote Azure Blob Storage backend and integrating it with your GitHub Actions CI/CD workflow.

## Step 1: Bootstrap the State Storage in Azure

Terraform needs a place to store its state file, but you can't easily use Terraform to create the storage account that will hold its own state. It's best to create this "bootstrap" infrastructure once using the Azure CLI.

Assuming you are logged in to the Azure CLI (`az login`), run these commands in your terminal to create the Storage Account and Container:

```bash
# 1. Create a dedicated Resource Group for the Terraform state
az group create --name rg-terraform-state --location eastasia

# 2. Create the Storage Account (name must be globally unique, e.g., tfstatemaas<random_number>)
az storage account create --resource-group rg-terraform-state --name tfstatemaas12345 --sku Standard_LRS --encryption-services blob

# 3. Create the Blob Container inside the Storage Account
az storage container create --name tfstate --account-name tfstatemaas12345
```

## Step 2: Update `main.tf`

Update `infra/terraform/main.tf` to tell Terraform to use the Blob Storage container you just created. Add the `backend` block inside your existing `terraform` block:

```hcl
# Core config for terraform.
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }

  # ADD THIS BLOCK: Configure the Azure Blob remote backend
  backend "azurerm" {
    resource_group_name  = "rg-terraform-state"
    storage_account_name = "tfstatemaas12345" # Use the exact name from Step 1
    container_name       = "tfstate"
    key                  = "prod.terraform.tfstate" # Name of the state file in the blob
  }
}
```

## Step 3: Migrate your Local State

Since you already have a local `terraform.tfstate` file, you need to migrate it to Azure.
Open your terminal, navigate to the `infra/terraform` directory, and run:

```bash
terraform init
```

Terraform will detect that you added a backend configuration and that you have a local state file. It will ask if you want to copy your existing state to the new backend. Type `yes`. 

Once this is done, you can safely delete the local `terraform.tfstate` and `terraform.tfstate.backup` files!

## Step 4: Add Terraform to CI/CD (GitHub Actions)

Now that your state is centralized in Azure, your CI/CD pipeline can read it to verify infrastructure changes. Let's create a workflow that runs `terraform plan` whenever someone opens a Pull Request modifying infrastructure.

Create a new file: `.github/workflows/terraform-plan.yaml`:

```yaml
name: Terraform Plan

on:
  pull_request:
    paths:
      - 'infra/terraform/**'

jobs:
  plan:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ./infra/terraform

    # You will need to add these credentials as GitHub Secrets, similar to your ACR setup.
    env:
      ARM_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}
      ARM_CLIENT_SECRET: ${{ secrets.AZURE_CLIENT_SECRET }}
      ARM_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      ARM_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}

    steps:
      - name: Checkout Code
        uses: actions/checkout@v6

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3

      - name: Terraform Format Check
        run: terraform fmt -check

      - name: Terraform Init
        run: terraform init

      - name: Terraform Plan
        # Generates an execution plan, showing what resources will be created/modified/destroyed.
        run: terraform plan -no-color
```

## Summary of Benefits

1. **Safety:** Your state file is no longer living locally on your laptop, reducing the risk of it being deleted or corrupted.
2. **Collaboration:** The remote backend automatically implements "State Locking" in Azure, preventing two concurrent operations from corrupting the state.
3. **CI/CD Visibility:** Every time you make a PR for an infrastructure change, the pipeline will output exactly what resources Terraform plans to change, allowing you to review the blast radius before merging.
