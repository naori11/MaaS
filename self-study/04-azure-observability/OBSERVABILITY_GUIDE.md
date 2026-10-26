# Practical Guide: Setting Up Log Analytics

This guide covers creating a Log Analytics Workspace and configuring your Azure VM's Docker daemon to send logs to it.

## Step 1: Create a Log Analytics Workspace via Terraform
Add this to your `infra/terraform/main.tf`:

```hcl
resource "azurerm_log_analytics_workspace" "maas_law" {
  name                = "law-maas-cluster"
  location            = azurerm_resource_group.maas_rg.location
  resource_group_name = azurerm_resource_group.maas_rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

# Output the Workspace ID and Key (needed to configure the agent)
output "law_workspace_id" {
  value = azurerm_log_analytics_workspace.maas_law.workspace_id
}
output "law_primary_key" {
  value = azurerm_log_analytics_workspace.maas_law.primary_shared_key
  sensitive = true
}
```

## Step 2: Install the Azure Monitor Agent on the VM
Azure provides a VM Extension to easily install the agent via Terraform:

```hcl
resource "azurerm_virtual_machine_extension" "ama" {
  name                       = "AzureMonitorLinuxAgent"
  virtual_machine_id         = azurerm_linux_virtual_machine.maas_vm.id
  publisher                  = "Microsoft.Azure.Monitor"
  type                       = "AzureMonitorLinuxAgent"
  type_handler_version       = "1.22"
  auto_upgrade_minor_version = true
}
```

## Step 3: Configure Docker Logging Driver
To send Docker container logs to Log Analytics, you can configure Docker's syslog driver to forward to the Azure Monitor Agent (which listens on syslog), or use a dedicated logging container like fluentbit.

The simplest approach for a single VM is adjusting `docker-compose.yml`:
```yaml
services:
  api-gateway:
    # ...
    logging:
      driver: "syslog"
      options:
        syslog-address: "udp://127.0.0.1:514"
        tag: "maas-api-gateway"
```

## Step 4: Query Logs
Once running, go to the Azure Portal -> Log Analytics Workspace -> Logs.
Run a KQL query:
```kusto
Syslog
| where ProcessName == "maas-api-gateway"
| where SyslogMessage contains "ERROR"
| sort by TimeGenerated desc
```
