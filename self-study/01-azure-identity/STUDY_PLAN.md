# Step 1: Azure Identity: Self-Study Plan

This module bridges the gap between using your personal Azure credentials and establishing secure, automated, machine-to-machine authentication.

---

## Module 1: The Core of Azure Identity (Microsoft Entra ID)
**Topics to Research:**
- Microsoft Entra ID (formerly Azure Active Directory) vs. traditional Active Directory.
- What is an "App Registration" vs. an "Enterprise Application".
- The concept of a "Service Principal" (the identity created for an application to access resources).

**Check for Understanding:**
1. If you want a GitHub Action to deploy infrastructure, does it log in as you (your personal email) or as something else?
2. What is the difference between a user identity and a service principal?

---

## Module 2: Role-Based Access Control (RBAC)
**Topics to Research:**
- The difference between Azure RBAC (for Azure resources like VMs, ACR) and Microsoft Entra ID roles (for managing users/directories).
- Scope: Management Group vs. Subscription vs. Resource Group vs. Resource.
- Common Built-in Roles: Reader, Contributor, Owner, AcrPull, Key Vault Secrets User.

**Check for Understanding:**
1. If your VM only needs to pull images from ACR, should you give it the "Contributor" role on the whole subscription? Why or why not?
2. What happens if a Service Principal has "Owner" at the Resource Group level?

---

## Module 3: Managed Identities
**Topics to Research:**
- System-assigned vs. User-assigned Managed Identities.
- How Managed Identities eliminate the need for managing credentials/secrets.
- How Azure VMs use the IMDS (Instance Metadata Service) to get tokens.

**Check for Understanding:**
1. If you delete a VM that has a System-assigned Managed Identity, what happens to the identity?
2. Why is a Managed Identity safer than passing a Client Secret to a VM as an environment variable?

---

## Module 4: OpenID Connect (OIDC) for GitHub Actions
**Topics to Research:**
- The dangers of storing long-lived Azure Client Secrets in GitHub.
- How OIDC works (federated identity).
- Configuring Federated Credentials in Azure App Registrations to trust a specific GitHub repository.

**Check for Understanding:**
1. With OIDC, does GitHub store a password for Azure? How does Azure know to trust the GitHub Action?
2. Can any GitHub repository assume your Service Principal if you set up OIDC? How is it restricted?
