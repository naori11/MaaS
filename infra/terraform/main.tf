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
}

# Configuration for the Azure Resource Manager provider fetched from the official registry.
provider "azurerm" {
  # Mandatory block to enable specific API behaviors for the provider. (Leave empty for default behavior.)
  features {}
  # This setting tells Terraform to skip the automatic registration of Azure resource providers.
  # Since we're only using a few core services (like Resource Groups and Virtual Networks), we can skip registering all the other providers that we won't be using, which can speed up the deployment process.
  # Also, we are only using an Azure for Students subscription, which has some limitations and might not allow certain providers to be registered.
  skip_provider_registration = "true"
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

  # RULE 2: Allow access to API Gateway (port 4000)
  # This rule allows incoming traffic to port 4000, which is the default port for the MAAS API Gateway.
  security_rule {
    name                       = "API-Gateway" # The name of the security rule, which is "API-Gateway" in this case.
    priority                   = "1002"        # The priority of the security rule, which determines the order in which rules are evaluated. Lower numbers have higher priority.
    direction                  = "Inbound"     # The direction of the traffic that the rule applies to, which is "Inbound" in this case, meaning it applies to incoming traffic to the resources associated with this NSG.
    access                     = "Allow"       # The action to take when the rule matches traffic, which is "Allow" in this case, meaning that matching traffic will be allowed through the NSG.
    protocol                   = "Tcp"         # The protocol that the rule applies to, which is "Tcp" in this case, meaning it applies to TCP traffic.
    source_port_range          = "*"           # The source port range for the rule, which is set to "*" in this case, meaning it applies to traffic from any source port.
    destination_port_range     = "4000"        # The destination port range for the rule, which is set to "4000" in this case, meaning it applies to traffic destined for port 4000 within the NSG.
    source_address_prefix      = "*"           # The source address prefix for the rule, which is set to "*" in this case, meaning it applies to traffic from any source IP address (any devices).
    destination_address_prefix = "*"           # The destination address prefix for the rule, which is set to "*" in this case, meaning it applies to traffic destined for any destination IP address (any resources, since the public IP is dynamic).
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
  size                = "Standard_B2ats_v2"                     # The size of the virtual machine, which determines the number of CPU cores, amount of RAM, and other resources allocated to the VM. "Standard_B1s" is a basic size suitable for small workloads and testing purposes.
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
  custom_data = base64encode(
    <<-EOF
    #!/bin/bash
    sudo apt-get update -y # Update the package lists for upgrades and new package installations.

    # Install necessary packages to prepare the system for Docker installation, including:
    # - ca-certificates: Ensures that the system can securely download packages over HTTPS.
    # - curl: A command-line tool for transferring data with URLs, used to download the Docker GPG key. 
    # - gnupg: A tool for managing GPG keys, required to add the Docker GPG key to the system's keyring.
    sudo apt-get install -y ca-certificates curl gnupg

    # Set up the Docker repository by adding the Docker GPG key and the Docker APT repository to the system's package sources.
    # This allows the system to securely download and install Docker packages from the official Docker repository.
    sudo install -m 0755 -d /etc/apt/keyrings

    # The "curl" command is used to download the Docker GPG key from the official Docker repository. 
    # The key is then processed with "gpg --dearmor" to convert it into a format suitable for use as an APT keyring, and saved to "/etc/apt/keyrings/docker.gpg".
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    
    # Set the permissions on the Docker GPG keyring file to ensure that it is readable by all users, which is necessary for the APT package manager to verify the authenticity of packages from the Docker repository.
    sudo chmod a+r /etc/apt/keyrings/docker.gpg

    # The "echo" command is used to add the Docker APT repository to the system's package sources.
    # It constructs a line that specifies the repository URL, the distribution (based on the current Ubuntu release), and the component (stable), and writes this line to a new file in "/etc/apt/sources.list.d/docker.list".
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Run the update command again to refresh the package lists, now including the Docker repository, so that the system is aware of the latest Docker packages available for installation.
    sudo apt-get update -y

    # Finally, install Docker and its related components, including:
    # - docker-ce: The Docker Engine, which is the core component of Docker that allows you to run and manage containers.
    # - docker-ce-cli: The command-line interface for Docker, which provides the "docker" command used to interact with the Docker Engine.
    # - containerd.io: A container runtime that Docker uses to manage container lifecycle.
    # - docker-buildx-plugin: A plugin for Docker Buildx, which is a tool for building multi-platform Docker images.
    # - docker-compose-plugin: A plugin for Docker Compose, which is a tool for defining and running multi-container Docker applications.
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Add the "azureuser" to the "docker" group to allow running Docker commands without needing to use "sudo".
    sudo usermod -aG docker azureuser
    EOF
  )
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
  admin_enabled       = true                                    # Enable the admin user account for the container registry, which allows you to authenticate and manage the registry using a username and password. This is useful for development and testing purposes, but in production, it's recommended to use more secure authentication methods, such as Azure Active Directory or service principals.
}

# Once the virtual machine is created, we can output the public IP address of the VM so that we can access it remotely.
output "public_ip_address" {
  value = azurerm_public_ip.maas_public_ip.ip_address # Output the public IP address of the virtual machine, which can be used to access the MAAS cluster remotely.
}
