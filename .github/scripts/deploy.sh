#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status

# Create docker-compose.yml file into the VM
mkdir -p /home/azureuser/app
echo '__COMPOSE_B64__' | base64 -d > /home/azureuser/app/docker-compose.yml

# Authenticate with Azure using the managed identity
az login --identity
az acr login --name acrmaascluster

# Fetch secrets from Key Vault into .env
VAULT='maas-kv-20261002'
echo "POSTGRES_USER=$(az keyvault secret show --vault-name $VAULT --name postgres-user --query value -o tsv)" > /home/azureuser/app/.env
echo "POSTGRES_PASSWORD=$(az keyvault secret show --vault-name $VAULT --name postgres-password --query value -o tsv)" >> /home/azureuser/app/.env
echo "JWT_SECRET=$(az keyvault secret show --vault-name $VAULT --name jwt-secret --query value -o tsv)" >> /home/azureuser/app/.env
echo "XENDIT_SECRET_KEY=$(az keyvault secret show --vault-name $VAULT --name xendit-secret-key --query value -o tsv)" >> /home/azureuser/app/.env
echo "XENDIT_CALLBACK_TOKEN=$(az keyvault secret show --vault-name $VAULT --name xendit-callback-token --query value -o tsv)" >> /home/azureuser/app/.env

# Set ownership and secure permissions for app directory and .env
chown -R azureuser:azureuser /home/azureuser/app
chmod 600 /home/azureuser/app/.env

# Delegate deployment to systemd
systemctl restart maas-app
