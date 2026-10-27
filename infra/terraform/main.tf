# -----------------------------------------
# Network Infrastructure for MAAS Cluster
# -----------------------------------------

# Core config for terraform.
terraform {
  # Tells terraform which cloud provider to use and which version.
  required_providers {
    # Official name for the Azure Resource Manger provider for Terraform.
    azurerm = {
      # Provide the source for the provider and the version to use from the official registry of HashiCorp.
      # The version is set to 3.0 or higher but less than 4.0.
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }

  # Backend configuration for storing Terraform state in Azure Blob Storage
  # This block specifically uploads the tfstate file in an azure blob storage container.
  backend "azurerm" {
    resource_group_name  = "rg-terraform-state"
    storage_account_name = "maastfstate1" # Use the exact name from Step 1
    container_name       = "tfstate"
    key                  = "prod.maas.tfstate" # Name of the state file in the blob
  }

}

# Configuration for the Azure Resource Manager provider fetched from the official registry.
provider "azurerm" {
  # Mandatory block to enable specific API behaviors for the provider. (Leave empty for default behavior.)
  features {}
  # This setting tells Terraform to skip the automatic registration of Azure resource providers.
  # Since we're only using a few core services (like Resource Groups and Virtual Networks), we can skip registering all the other providers that we won't be using, which can speed up the deployment process.
  # Also, we are only using an Azure for Students subscription, which has some limitations and might not allow certain providers to be registered.
  # But since we are using a fresh subscription, we set this to false (or remove it) so that Terraform can automatically register the namespaces (e.g. Microsoft.Network, Microsoft.Compute) required by our resources.
  skip_provider_registration = false
}

# Define a resource group in Azure where all the resources for the MAAS cluster will be created.
# "azurerm_resource_group" is the resource type for creating a resource group in Azure, provided by the azurerm provider.
# "maas_rg" is the name of this specific resource instance, which can be referenced later within the code.
resource "azurerm_resource_group" "maas_rg" {
  name     = "rg-maas-cluster" # The name of the resource group to be created in Azure.
  location = "eastasia"        # The Azure region where the resource group and all its resources will be located.

}

# -----------------------------------------
# Network Infrastructure for MAAS Cluster
# -----------------------------------------

# DEPENDENCY GRAPH IN ACTION:
# Notice we do NOT hardcode the location or resource group name in these resources.
# We dynamically reference the exact box we created earlier.
# This tells Terraform: "Don't build this until the Resource Group exists."

# Define a virtual network in Azure for the MAAS cluster.
# "azurerm_virtual_network" is the resource type for creating a virtual network in Azure, provided by the azurerm provider.
resource "azurerm_virtual_network" "maas_vnet" {
  name = "vnet-maas-cluster" # The name of the virtual network to be created in Azure.
  # The address space for the virtual network, which defines the range of IP addresses that can be used within this network.
  # In this case, it's set to "10.0.0.0/16".
  # Definitely gonna need to study networking concepts and subnetting to understand this better.
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.maas_rg.location # The location and resource group for the virtual network are set to be the same as the resource group defined above.
  resource_group_name = azurerm_resource_group.maas_rg.name     # The name of the resource group where the virtual network will be created, referencing the resource group defined above.

}

# Define a subnet within the virtual network for the MAAS cluster.
# "azurerm_subnet" is the resource type for creating a subnet in Azure, provided by the azurerm provider.
resource "azurerm_subnet" "maas_subnet" {
  name = "subnet-maas-cluster" # The name of the subnet to be created within the virtual network.
  # The address prefix for the subnet, which defines the range of IP addresses that can be used within this subnet.
  # In this case, it's set to "10.0.0.0/24".
  address_prefixes = ["10.0.0.0/24"]

  # DEPENDENCY GRAPH IN ACTION:
  # Again, we reference the virtual network we created in the previous step.
  # This tells Terraform: "Don't build this until the Virtual Network exists."

  virtual_network_name = azurerm_virtual_network.maas_vnet.name # The name of the virtual network where the subnet will be created, referencing the virtual network defined above.
  resource_group_name  = azurerm_resource_group.maas_rg.name    # The name of the resource group where the subnet will be created, referencing the resource group defined above.
}

# -----------------------------------------
# Network Configuration for the MAAS Cluster
# -----------------------------------------

# Define a public IP address in Azure for the MAAS cluster.
# "azurerm_public_ip" is the resource type for creating a public IP address in Azure, provided by the azurerm provider.
resource "azurerm_public_ip" "maas_public_ip" {
  name                = "pip-maas-cluster"                      # The name of the public IP address resource to be created in Azure.
  location            = azurerm_resource_group.maas_rg.location # The location where the public IP address will be created, referencing the resource group defined above.
  resource_group_name = azurerm_resource_group.maas_rg.name     # The name of the resource group where the public IP address will be created, referencing the resource group defined above.
  # Set the allocation method for the public IP address to "Dynamic", which means that Azure will automatically assign an available IP address from its pool when the resource is created.
  # Mainly to reduce cost, since static IPs have recurring cost in Azure.
  # But since our account is Azure for Students, we have no access in using Dynamic IPs.
  allocation_method = "Static"
  sku               = "Standard" # The SKU (Stock Keeping Unit) for the public IP address, which determines the features and pricing tier. "Standard" provides better performance and availability compared to "Basic", but it also has a higher cost. In this case, we choose "Standard" to ensure better performance for the MAAS cluster, especially since it will be accessed remotely and may require more reliable connectivity.
}

# Define a network security group in Azure for the MAAS cluster.
# "azurerm_network_security_group" is the resource type for creating a network security group in Azure, provided by the azurerm provider.
resource "azurerm_network_security_group" "maas_nsg" {
  name                = "nsg-maas-cluster"                      # The name of the network security group to be created in Azure.
  location            = azurerm_resource_group.maas_rg.location # The location where the network security group will be created, referencing the resource group defined above.
  resource_group_name = azurerm_resource_group.maas_rg.name     # The name of the resource group where the network security group will be created, referencing the resource group defined above.

  # Define security rules for the network security group.

  # RULE 1: Allow SSH
  # This rule allows incoming SSH traffic to the resources associated with this NSG, which is essential for managing the MAAS cluster remotely via SSH.
  # Github Actions will also use this port to connect to the MAAS cluster and run commands on the nodes for provisioning and management.
  security_rule {
    name                       = "SSH"     # The name of the security rule, which is "SSH" in this case.
    priority                   = "1001"    # The priority of the security rule, which determines the order in which rules are evaluated. Lower numbers have higher priority.
    direction                  = "Inbound" # The direction of the traffic that the rule applies to, which is "Inbound" in this case, meaning it applies to incoming traffic to the resources associated with this NSG.
    access                     = "Allow"   # The action to take when the rule matches traffic, which is "Allow" in this case, meaning that matching traffic will be allowed through the NSG.
    protocol                   = "Tcp"     # The protocol that the rule applies to, which is "Tcp" in this case, meaning it applies to TCP traffic.
    source_port_range          = "*"       # The source port range for the rule, which is set to "*" in this case, meaning it applies to traffic from any source port.
    destination_port_range     = "22"      # The destination port range for the rule, which is set to "22" in this case, meaning it applies to traffic destined for port 22 within the NSG, which is the default port for SSH.
    source_address_prefix      = "*"       # The source address prefix for the rule, which is set to "*" in this case, meaning it applies to traffic from any source IP address (any devices).
    destination_address_prefix = "*"       # The destination address prefix for the rule, which is set to "*" in this case, meaning it applies to traffic destined for any destination IP address (any resources, since the public IP is dynamic).
  }

  # -------------------------------------------------------------------------------------------------
  # [PREVIOUS RULE - Kept for study reference]:
  # Originally, API Gateway port 4000 is directly exposed to the internet.
  # Now that NGINX is our edge reverse proxy, clients should never hit port 4000 directly.
  # Instead, traffic enters strictly via standard web ports (80 and 443).
  #
  # security_rule {
  #   name                       = "API-Gateway"
  #   priority                   = "1002"
  #   direction                  = "Inbound"
  #   access                     = "Allow"
  #   protocol                   = "Tcp"
  #   source_port_range          = "*"
  #   destination_port_range     = "4000"
  #   source_address_prefix      = "*"
  #   destination_address_prefix = "*"
  # }
  # -------------------------------------------------------------------------------------------------

  # RULE 2: Allow HTTP (port 80)
  # Allows incoming HTTP traffic so NGINX can redirect clients to secure HTTPS (301 redirect).
  security_rule {
    name                       = "HTTP"
    priority                   = "1002"
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  # RULE 3: Allow HTTPS (port 443)
  # Allows encrypted HTTPS web traffic reaching NGINX edge reverse proxy for SSL termination.
  security_rule {
    name                       = "HTTPS"
    priority                   = "1003"
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

# -----------------------------------------
# Network Interface and Virtual Machine
# -----------------------------------------

# Define a network interface in Azure for the MAAS cluster.
# "azurerm_network_interface" is the resource type for creating a network interface in Azure, provided by the azurerm provider.
resource "azurerm_network_interface" "maas_nic" {
  name                = "nic-maas-cluster"                      # The name of the network interface to be created in Azure.
  location            = azurerm_resource_group.maas_rg.location # The location where the network interface will be created, referencing the resource group defined above.
  resource_group_name = azurerm_resource_group.maas_rg.name     # The name of the resource group where the network interface will be created, referencing the resource group defined above.

  ip_configuration {
    name                          = "internal"                          # The name of the IP configuration for the network interface, which is "internal" in this case.
    subnet_id                     = azurerm_subnet.maas_subnet.id       # The ID of the subnet where the network interface will be connected, referencing the subnet defined above.
    private_ip_address_allocation = "Dynamic"                           # IP address allocation within the subnet. Set to "Dynamic" to allow Azure to automatically assign an available private IP address from the subnet's address range when the resource is created.
    public_ip_address_id          = azurerm_public_ip.maas_public_ip.id # The public IP address to associate with the network interface, referencing the public IP defined above.
  }

}

# Associate the network security group with the network interface.
# "azurerm_network_interface_security_group_association" is the resource type for associating a network security group with a network interface in Azure, provided by the azurerm provider.
resource "azurerm_network_interface_security_group_association" "maas_nic_nsg_assoc" {
  network_interface_id      = azurerm_network_interface.maas_nic.id      # The ID of the network interface to associate with the NSG, referencing the network interface defined above.
  network_security_group_id = azurerm_network_security_group.maas_nsg.id # The ID of the network security group to associate with the network interface, referencing the NSG defined above.
}

# Define the virtual machine in Azure for the MAAS cluster.
# "azurerm_linux_virtual_machine" is the resource type for creating a Linux virtual machine
resource "azurerm_linux_virtual_machine" "maas_vm" {
  name                = "vm-maas-cluster"                       # The name of the virtual machine to be created in Azure.
  resource_group_name = azurerm_resource_group.maas_rg.name     # The name of the resource group where the virtual machine will be created, referencing the resource group defined above.
  location            = azurerm_resource_group.maas_rg.location # The location where the virtual machine will be created, referencing the resource group defined above.
  size                = "Standard_B2als_v2"                     # The size of the virtual machine, which determines the number of CPU cores, amount of RAM, and other resources allocated to the VM. "Standard_B1s" is a basic size suitable for small workloads and testing purposes.
  admin_username      = "azureuser"                             # The username for the administrator account on the virtual machine. This is the account that will be used to log in to the VM and perform administrative tasks. In production, it's recommended to use a more secure method for managing credentials, such as Azure Key Vault or Terraform variables, instead of hardcoding them in the code.
  # admin_password      = "P@ssw0rd1234!"                         # In production, use a more secure method for managing credentials, such as Azure Key Vault or Terraform variables.

  # Attach the network interface to the virtual machine.
  # This tells Azure which network interface (and therefore which subnet and public IP) to use for this VM.
  network_interface_ids = [
    azurerm_network_interface.maas_nic.id
  ]

  # SSH key-based authentication for the virtual machine.
  # This is a more secure method than using passwords, as it relies on cryptographic keys instead of shared secrets.
  admin_ssh_key {
    username   = "azureuser"
    public_key = file("~/.ssh/id_rsa.pub") # Path to your SSH public key for secure access to the VM.
  }

  # Configure the operating system disk for the virtual machine.
  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  # Configure the source image for the virtual machine. This specifies which operating system image to use when creating the VM.
  # In this case, we're using a specific Ubuntu Server 22.04 LTS image from the Azure Marketplace.
  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts"
    version   = "latest"
  }

  # The "custom_data" field allows you to provide a script that will be executed on the virtual machine when it is first provisioned.
  # It updates the server and silently installs Docker and Docker Compose.
  custom_data = base64encode(<<-EOF
#!/bin/bash
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl gnupg

# Set up Docker repository
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Install Azure CLI for Identity Management
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Add azureuser to docker group
sudo usermod -aG docker azureuser

# Create app directory
mkdir -p /home/azureuser/app
chown -R azureuser:azureuser /home/azureuser/app

# Create the systemd service file for the Docker Compose application
cat <<'SERVICE' > /etc/systemd/system/maas-app.service
[Unit]
Description=MaaS Docker Compose Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/azureuser/app
ExecStartPre=/usr/bin/az login --identity
ExecStartPre=/usr/bin/az acr login --name acrmaascluster
ExecStart=/usr/bin/docker compose pull
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down

[Install]
WantedBy=multi-user.target
SERVICE

# Reload systemd and enable the service on boot
systemctl daemon-reload
systemctl enable maas-app
EOF
  )

  # ---------------------------------------------------------------------------------------------------------
  # AZURE IDENTITY (Managed Identity):
  # A Service Principal is an identity created for an application or machine rather than a human user.
  # By setting type to "SystemAssigned", Azure automatically creates a Service Principal in Microsoft Entra ID tied directly to the lifecycle of this VM.
  # ---------------------------------------------------------------------------------------------------------
  identity {
    type = "SystemAssigned"
  }

}

# -----------------------------------------
# Azure Container Registry (ACR) for MAAS Cluster
# -----------------------------------------

# Define an Azure Container Registry (ACR) for the MAAS cluster.
# "azurerm_container_registry" is the resource type for creating a container registry in Azure, provided by the azurerm provider.
resource "azurerm_container_registry" "maas_acr" {
  name                = "acrmaascluster"                        # The name of the Azure Container Registry to be created in Azure.
  resource_group_name = azurerm_resource_group.maas_rg.name     # The name of the resource group where the container registry will be created, referencing the resource group defined above.
  location            = azurerm_resource_group.maas_rg.location # The location where the container registry will be created, referencing the resource group defined above.
  sku                 = "Basic"                                 # The SKU (Stock Keeping Unit) for the container registry, which determines the features and pricing tier. "Basic" is a cost-effective option suitable for development and testing scenarios, providing essential features for storing and managing container images.

  # As noted in MANUAL_NOTES.md:
  # Turning off "admin_enabled" (false) disables the legacy shared username/password for the registry.
  # Instead of using shared static passwords, all access is governed through Azure RBAC (least privilege).
  admin_enabled = false
}

# -----------------------------------------
# Azure Role-Based Access Control (RBAC) for MAAS Cluster
# -----------------------------------------

# ---------------------------------------------------------------------------------------------------------
# AZURE RBAC (Role-Based Access Control) ROLE ASSIGNMENT:
#
# 1. Resource Level (Scope) (What resource would be given access to):
#    - Scope is set to the individual ACR resource ID (`azurerm_container_registry.maas_acr.id`).
#    - Following the scope hierarchy (Management Group -> Subscription -> Resource Group -> Resource),
#      this grants permissions ONLY to this specific ACR, not the entire subscription or resource group.
#
# 2. Data Plane Role ("AcrPull") (The permissions granted to the identity):
#    - Azure separates Control Plane (managing the resource) from Data Plane (accessing content).
#    - "AcrPull" is a Data Plane role allowing the identity to pull container images (`docker pull`),
#      without granting permissions to push images, delete repositories, or alter ACR configuration.
#
# 3. Principal ID (The identity that is being granted the role):
#    - Points to `azurerm_linux_virtual_machine.maas_vm.identity[0].principal_id`, which is the
#      Object ID of the VM's Service Principal generated in Microsoft Entra ID.
# ---------------------------------------------------------------------------------------------------------

# Define the role assignment for the VM to pull from the ACR
# "azurerm_role_assignment" is the resource type used to assign a role to a principal (VM identity) at the resource level (ACR).
resource "azurerm_role_assignment" "vm_acr_pull" {
  # Which resource to assign the role to (ACR in this case) (Who?)
  principal_id = azurerm_linux_virtual_machine.maas_vm.identity[0].principal_id
  # Which role to assign (AcrPull allows the identity to pull container images) (What?)
  role_definition_name = "AcrPull"
  # What resource to assign the role to (ACR in this case) (Where?)
  scope = azurerm_container_registry.maas_acr.id

}

# -----------------------------------------
# Azure Key Vault for MAAS Cluster
# -----------------------------------------

# Data source to get the current Azure client configuration (subscription ID, tenant ID, object ID, etc.)
data "azurerm_client_config" "current" {}

# Define the Azure Key Vault for the MAAS cluster
# "azurerm_key_vault" is a resource that allows you to create and manage Azure Key Vaults.
resource "azurerm_key_vault" "maas_kv" {
  name                = "maas-kv-20261002"                           # The name of the key vault to be created in Azure.
  location            = azurerm_resource_group.maas_rg.location      # The Azure region where the key vault will be created.
  resource_group_name = azurerm_resource_group.maas_rg.name          # The name of the resource group where the key vault will be created.
  tenant_id           = data.azurerm_client_config.current.tenant_id # The tenant ID of the Azure subscription.
  sku_name            = "standard"                                   # The SKU name of the key vault (standard or premium). (Tier of the key vault)

  # Use the modern Azure RBAC instead of the legacy Access Policies.
  enable_rbac_authorization = true
}

# Define the role assignment for the home tenant to make CRUD operations on the key vault.
# "azurerm_role_assignment" is the resource type used to assign a role to a principal (The home tenant in this case) at the resource level (Key Vault).
resource "azurerm_role_assignment" "tf_kv_officer" {
  role_definition_name = "Key Vault Secrets Officer"                  # Which role to assign (Allow CRUD operations on secrets) (What?)
  scope                = azurerm_key_vault.maas_kv.id                 # What resource to assign the role to (the key vault in this case) (Where?)
  principal_id         = data.azurerm_client_config.current.object_id # Who to assign the role to (the home tenant in this case) (Who?)

}

# -----------------------------------------
# Azure Key Vault Secrets Provisioning
# -----------------------------------------

# Define the secrets to be stored in the key vault.
# Secrets are declared as variables under the "variables.tf" file.
locals {                                     # locals block is used to define local variables that can be used throughout the Terraform configuration.
  app_secrets = {                            # app_secrets is a local variable that holds the secrets to be stored in the key vault.
    "jwt-secret"            = var.jwt_secret # Referenced from the "variables.tf" file.
    "xendit-secret-key"     = var.xendit_secret_key
    "xendit-callback-token" = var.xendit_callback_token
    "postgres-user"         = var.postgres_user
    "postgres-password"     = var.postgres_password
  }
}

# Create the secrets in the key vault.
resource "azurerm_key_vault_secret" "app_secrets" {
  for_each     = local.app_secrets            # Iterate over the app_secrets local variable and create a secret for each key-value pair.
  name         = each.key                     # The name of the secret to be created in the key vault.
  value        = each.value                   # The value of the secret to be stored in the key vault.
  key_vault_id = azurerm_key_vault.maas_kv.id # The ID of the key vault where the secret will be stored.

  # Ensures the role assignment is complete before creating the secret.
  # This makes sure that terraform has write permissions before attempting to add the secret to the key vault.
  depends_on = [azurerm_role_assignment.tf_kv_officer]
}

# Define the role assignment for the virtual machine to read secrets from the key vault.
resource "azurerm_role_assignment" "vm_kv_reader" {
  role_definition_name = "Key Vault Secrets User"                                       # Which role to assign (Allow read operations on secrets) (What?)
  scope                = azurerm_key_vault.maas_kv.id                                   # What resource to assign the role to (the key vault in this case) (Where?)
  principal_id         = azurerm_linux_virtual_machine.maas_vm.identity[0].principal_id # Who to assign the role to (the virtual machine in this case) (Who?)
}

# -----------------------------------------
# Azure Observability (Log Analytics, Azure Monitor, DCR)
# -----------------------------------------

# Define the Log Analytics Workspace (LAW) for the virtual machine.
# "azurerm_log_analytics_workspace" is a resource type that allows you to create a Log Analytics workspace in Azure.
resource "azurerm_log_analytics_workspace" "maas_law" {
  name                = "law-maas-cluster"                      # The name of the Log Analytics workspace to be created.
  location            = azurerm_resource_group.maas_rg.location # The Azure region where the Log Analytics workspace will be created.
  resource_group_name = azurerm_resource_group.maas_rg.name     # The name of the resource group to which the Log Analytics workspace will be assigned.
  sku                 = "PerGB2018"                             # The SKU (pricing tier) of the Log Analytics workspace.
  retention_in_days   = 30                                      # The number of days to retain logs in the Log Analytics workspace.
}

# Define the Azure Monitor Agent (AMA) extension for the virtual machine.
# "azurerm_virtual_machine_extension" is a resource type that allows you to install an extension on a virtual machine in Azure.
resource "azurerm_virtual_machine_extension" "ama" {
  name                       = "AzureMonitorLinuxAgent"                 # The name of the extension to be installed.
  virtual_machine_id         = azurerm_linux_virtual_machine.maas_vm.id # The ID of the virtual machine to install the extension on.
  publisher                  = "Microsoft.Azure.Monitor"                # The publisher of the extension.
  type                       = "AzureMonitorLinuxAgent"                 # The type of the extension.
  type_handler_version       = "1.28"                                    # The version of the extension handler to use.
  auto_upgrade_minor_version = true                                     # Automatically upgrade to the latest minor version of the extension.

  depends_on = [azurerm_linux_virtual_machine.maas_vm] # The virtual machine must be created before the extension can be installed.
}

# Define the Data Collection Rule (DCR) for the virtual machine.
# "azurerm_data_collection_rule" is a resource type that allows you to create a Data Collection Rule in Azure.
resource "azurerm_monitor_data_collection_rule" "maas_dcr" {
  name                = "dcr-maas-cluster"                      # The name of the Data Collection Rule to be created.
  resource_group_name = azurerm_resource_group.maas_rg.name     # The name of the resource group where the Data Collection Rule will be created.
  location            = azurerm_resource_group.maas_rg.location # The location where the Data Collection Rule will be created, referencing the resource group defined above.

  destinations {
    log_analytics {
      workspace_resource_id = azurerm_log_analytics_workspace.maas_law.id # The ID of the Log Analytics workspace where the data will be sent.
      name                  = "law-destination"                           # The name of the destination within the Data Collection Rule.
    }
  }

  data_sources {
    syslog {
      facility_names = ["daemon", "syslog", "local0"] # Capture syslog messages from system daemons, syslog system, and local0, which is used for custom app logging.
      log_levels     = ["*"]                          # Set the log level to capture all syslog messages.
      name           = "syslog-datasource"            # The name of the syslog data source.
      streams        = ["Microsoft-Syslog"]           # Standardized schema for formatting syslog messages. Allows stream of logs to flow directly into the Microsoft Syslog schema stream.
    }
  }

  data_flow {
    streams      = ["Microsoft-Syslog"] # The stream to use for the data flow. Any data flowing into the specific stream will be collected and sent to the destinations.
    destinations = ["law-destination"]  # The destination to send the collected data to. In this case, it is the LAW (Log Analytics Workspace) destination.
  }
}

# DCR Rule association
# Associate the DCR Rule with the VM
resource "azurerm_monitor_data_collection_rule_association" "maas_dcr_association" {
  name                    = "dcr-maas-vm"                                    # The name of the association.
  target_resource_id      = azurerm_linux_virtual_machine.maas_vm.id         # The ID of the target resource to associate with the DCR Rule.
  data_collection_rule_id = azurerm_monitor_data_collection_rule.maas_dcr.id # The ID of the Data Collection Rule to associate with the target resource.
}

output "law_workspace_id" {
  value = azurerm_log_analytics_workspace.maas_law.workspace_id # Output the ID of the Log Analytics workspace, which can be used to access the data collected by the DCR Rule.
}

# Once the virtual machine is created, we can output the public IP address of the VM so that we can access it remotely.
output "public_ip_address" {
  value = azurerm_public_ip.maas_public_ip.ip_address # Output the public IP address of the virtual machine, which can be used to access the MAAS cluster remotely.
}
