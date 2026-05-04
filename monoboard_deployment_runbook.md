# 🚀 Monoboard AI: Live Azure Deployment Runbook

This runbook provides the exact steps to deploy the Monoboard Agent Governance ecosystem into your Azure tenant.

**Target Region**: `East US`
**Resource Group**: `agent-monoboard-prod`

---

## Phase 1: Azure Infrastructure Setup

Create the following resources in the `agent-monoboard-prod` resource group.

### 1. Storage Account
- **Name**: `stmonoboardprodlog` (must be globally unique)
- **Use**: Hosting the `agentruns` Table Storage.

### 2. Function Apps (Python 3.11, Consumption Plan)
Create 5 Function Apps with the following names:
1. `monoboard-validator`
2. `monoboard-rfi-router`
3. `monoboard-change-order`
4. `monoboard-daily-report`
5. `monoboard-ceo-agent`

---

## Phase 2: OIDC Security Setup (Entra ID)

To allow GitHub Actions to deploy code without using passwords/secrets, we use OpenID Connect (OIDC).

1. **Create App Registration**:
   - Go to **Microsoft Entra ID** -> **App registrations** -> **New registration**.
   - Name: `monoboard-github-deployer`.
2. **Add Federated Credentials**:
   - Go to the new registration -> **Certificates & secrets** -> **Federated credentials** -> **Add credential**.
   - **Federated credential scenario**: `GitHub Actions deploying Azure resources`.
   - **Organization**: Your GitHub Username/Org.
   - **Repository**: `monoboard.ai` (or your repo name).
   - **Entity type**: `Branch`.
   - **Branch**: `main`.
3. **Assign Permissions**:
   - Go to your **Subscription** -> **Access control (IAM)** -> **Add role assignment**.
   - **Role**: `Contributor`.
   - **Assign access to**: `User, group, or service principal`.
   - **Select**: `monoboard-github-deployer`.

---

## Phase 3: GitHub Configuration

Add the following **Secrets** to your GitHub Repository:
`Settings` -> `Secrets and variables` -> `Actions`.

| Secret Name | Value Source |
| --- | --- |
| `AZURE_CLIENT_ID` | The **Application (client) ID** of `monoboard-github-deployer`. |
| `AZURE_TENANT_ID` | Your Azure **Directory (tenant) ID**. |
| `AZURE_SUBSCRIPTION_ID` | Your Azure **Subscription ID**. |

---

## Phase 4: Azure App Settings (Environment Variables)

In the Azure Portal, go to each Function App -> **Settings** -> **Configuration** -> **Application settings**.

### For ALL Agents (RFI, CO, Daily, CEO)
- `AZURE_OPENAI_ENDPOINT`: Your Azure OpenAI Service endpoint.
- `AZURE_OPENAI_KEY`: Your Azure OpenAI API Key.
- `AZURE_OPENAI_DEPLOYMENT`: The name of your GPT-4/GPT-3.5 deployment.
- `VALIDATOR_API_URL`: `https://monoboard-validator.azurewebsites.net/api/validate`

### For the Validator App
- `AZURE_TABLE_CONNECTION_STRING`: Connection string for `stmonoboardprodlog`.
- `SP_TENANT_ID`: Your M365 Tenant ID.
- `SP_SITE_ID`: The SharePoint Site ID where your matrices live.

---

## Phase 5: Trigger Deployment

Once the steps above are complete, simply push a small change to your `main` branch. GitHub Actions will:
1. Run all `pytest` suites in parallel.
2. If tests pass, it will securely deploy the code to all 5 Azure Function Apps.

> [!CHECKPOINT]
> After deployment, you can verify the status by visiting the CEO Agent's manual endpoint:
> `https://monoboard-ceo-agent.azurewebsites.net/api/manual_governance_report`
