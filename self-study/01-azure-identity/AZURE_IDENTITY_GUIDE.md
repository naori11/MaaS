# Practical Guide: Setting Up Azure Identity & OIDC

This guide walks through creating a Service Principal for your GitHub Actions and using OIDC so you don't have to store long-lived secrets in GitHub.

## Step 1: Create an App Registration / Service Principal
We will create a Service Principal for your CI/CD pipeline.

```bash
# Create an app registration
az ad app create --display-name "MaaS-GitHub-Actions"

# Get the Application (Client) ID and Object ID
appId=$(az ad app list --display-name "MaaS-GitHub-Actions" --query "[0].appId" -o tsv)
objectId=$(az ad app list --display-name "MaaS-GitHub-Actions" --query "[0].id" -o tsv)

# Create a Service Principal for the App
az ad sp create --id $appId
```

## Step 2: Assign RBAC Roles
Grant this Service Principal the "Contributor" role on your subscription so it can run Terraform.

```bash
# Get your Subscription ID
subId=$(az account show --query id -o tsv)

# Assign Contributor role to the Service Principal
az role assignment create --assignee $appId --role Contributor --scope /subscriptions/$subId
```

## Step 3: Setup Federated Credentials (OIDC)
Instead of generating a password (client secret), tell Azure to trust your GitHub repository.

Create a file named `credential.json`:
```json
{
    "name": "github-actions-maas",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:YOUR-GITHUB-USERNAME/MaaS:ref:refs/heads/master",
    "description": "Trust GitHub Actions for MaaS repo",
    "audiences": ["api://AzureADTokenExchange"]
}
```
Run this to apply the federated credential:
```bash
az ad app federated-credential create --id $objectId --parameters @credential.json
```

## Step 4: Configure GitHub Actions
In your `.github/workflows/terraform-plan.yaml`, configure the Azure Login action using OIDC.
First, add these to your GitHub Repo Variables (not secrets, variables are fine here):
- `AZURE_CLIENT_ID` (the `$appId` from above)
- `AZURE_TENANT_ID` (run `az account show --query tenantId -o tsv`)
- `AZURE_SUBSCRIPTION_ID` (`$subId`)

Update your workflow to request OIDC permissions:
```yaml
permissions:
  id-token: write # Required for OIDC
  contents: read

jobs:
  plan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Azure Login
        uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
      
      # Now run terraform!
```
