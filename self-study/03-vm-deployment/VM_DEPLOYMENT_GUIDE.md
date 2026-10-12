# Practical Guide: Deploying to the VM

This guide walks through configuring the Azure VM to securely pull images from ACR and run your Docker Compose stack automatically on boot.

## Step 1: Enable Managed Identity and ACR Pull
Update your `main.tf` to give the VM an identity and permission to read from your ACR.

```hcl
# 1. Add Identity to VM
resource "azurerm_linux_virtual_machine" "maas_vm" {
  # ... (existing config) ...
  
  identity {
    type = "SystemAssigned"
  }
}

# 2. Grant VM access to ACR
resource "azurerm_role_assignment" "vm_acr_pull" {
  scope                = azurerm_container_registry.maas_acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_linux_virtual_machine.maas_vm.identity[0].principal_id
}
```

## Step 2: The systemd Service File
You want Docker Compose to run automatically when the VM boots. We'll create a `systemd` service.

On the VM, create `/etc/systemd/system/maas-app.service`:
```ini
[Unit]
Description=MaaS Docker Compose Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/azureuser/MaaS
ExecStartPre=/usr/bin/az login --identity
ExecStartPre=/usr/bin/az acr login --name acrmaascluster 
ExecStart=/usr/bin/docker compose pull
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down

[Install]
WantedBy=multi-user.target
```

Enable it so it starts on boot:
```bash
sudo systemctl enable maas-app
sudo systemctl start maas-app
```

## Step 3: CI/CD Pipeline Update
When a developer merges code, GitHub Actions should update the VM.
A simple way (though self-hosted runners are more secure) is to SSH into the VM and trigger a restart.

In `.github/workflows/deploy.yaml`:
```yaml
      - name: Deploy to VM
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.VM_PUBLIC_IP }}
          username: azureuser
          key: ${{ secrets.VM_SSH_PRIVATE_KEY }}
          script: |
            cd ~/MaaS
            git pull origin master
            sudo systemctl restart maas-app
```
*(Note: This requires opening SSH on the NSG, or better, using a self-hosted runner).*
