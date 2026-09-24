# Setting Up a Service Principal for GitHub Actions (OIDC)

For setting up a Service Principal for (GitHub Actions)

Run the following commands:

---

## 1. Create App Registration

```powershell
# Create the app registration for GitHub Actions
$app = az ad app create --display-name "MaaS-GitHub-Actions"

# If the app already exists, get the first record
$app = az ad app list --display-name "MaaS-GitHub-Actions" | ConvertFrom-Json | Select-Object -First 1
```

---

## 2. Extract Application ID and Object ID

```powershell
# Extract the Application ID and Object ID
$appId = $app.appId # The app's public identifier
$objectId = $app.id # The unique identifier for the record within Entra ID
```

### Parameter Breakdown

| Variable | Description / Note |
| :--- | :--- |
| `appId` | The app's public identifier |
| `objectId` | The unique identifier for the record within Entra ID |

---

## 3. Create Service Principal

> **Note:** Grants permissions to the app to access Azure resources by providing a role assignment to the app's Application ID.

```powershell
# Create the Service Principal for the GitHub Actions app
# Grants permissions to the app to access Azure resources by providing a role assignment to the app's Application ID
az ad sp create --id $appId
```

---

## 4. Get Subscription ID and Tenant ID

```powershell
# Get your Subscription ID and Tenant ID
$subId = (az account show --query id -o tsv)
$tenantId = (az account show --query tenantId -o tsv)
```

---

## 5. Assign Roles to the Service Principal

```powershell
# Assign Contributor and AcrPush roles to the Service Principal
az role assignment create --role "Contributor" --scope "/subscriptions/$subId" --assignee $appId
az role assignment create --role "AcrPush" --scope "/subscriptions/$subId" --assignee $appId
```

---

## 6. Create OIDC Federation Credentials for GitHub Actions

Azure CLI requires federated credential settings to be passed via the `--parameters` argument as a JSON file or inline JSON string.

### `credential.json` Content
```json
{
  "name": "github-actions-master",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:naori11/MaaS:ref:refs/heads/master",
  "description": "Trust GitHub Actions for MaaS master branch",
  "audiences": [
    "api://AzureADTokenExchange"
  ]
}
```

### Parameter Reference

| Parameter | Description / Note |
| :--- | :--- |
| `name` | The name identifier for the federated credential |
| `issuer` | The token issuer URL linked to GitHub's official token service (`https://token.actions.githubusercontent.com`) |
| `subject` | The specific repository and branch filter (`repo:<owner>/<repo>:ref:refs/heads/<branch>`) |
| `description` | Contextual note describing the purpose of the credential |
| `audiences` | Standard Azure token exchange protocol identifier (`api://AzureADTokenExchange`) |

### Runnable PowerShell Command

```powershell
# Create the federated credential using credential.json
az ad app federated-credential create --id $objectId --parameters credential.json
```

---

## Complete Setup Script

```powershell
# 1. Create the app registration for GitHub Actions
$app = az ad app create --display-name "MaaS-GitHub-Actions" | ConvertFrom-Json

# If the app already exists, retrieve it:
# $app = az ad app list --display-name "MaaS-GitHub-Actions" | ConvertFrom-Json | Select-Object -First 1

# 2. Extract the Application ID and Object ID
$appId = $app.appId # The app's public identifier
$objectId = $app.id # The unique identifier for the record within Entra ID

# 3. Create the Service Principal for the GitHub Actions app
# Grants permissions to the app to access Azure resources by providing a role assignment to the app's Application ID
az ad sp create --id $appId

# 4. Get your Subscription ID and Tenant ID
$subId = (az account show --query id -o tsv)
$tenantId = (az account show --query tenantId -o tsv)

# 5. Assign Contributor and AcrPush roles to the Service Principal at the Subscription level
az role assignment create --role "Contributor" --scope "/subscriptions/$subId" --assignee $appId
az role assignment create --role "AcrPush" --scope "/subscriptions/$subId" --assignee $appId

# 6. Create the OIDC Federation Credentials for GitHub Actions
az ad app federated-credential create --id $objectId --parameters credential.json
```
