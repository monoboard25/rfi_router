# Monoboard Validator Chain

The Validator Chain is a serverless Azure Function (Python) responsible for enforcing the Phase 0 operational directives on all AI agents before they are permitted to execute writes in the Microsoft 365 environment.

It contains four validators:
1. **Schema**: Ensures the output payload strictly matches the agent's expected JSON schema.
2. **Scope**: Cross-references the write target against the Permission Matrix to ensure proper bounds.
3. **Naming**: Enforces the project and company file naming conventions.
4. **Escalation**: Evaluates output against the Escalation Matrix DSL to route high-stakes actions to human review.

## Local Development

We use `uv` for ultra-fast dependency management.

### Setup
```bash
cd validator
uv sync
```

### Running Tests
The test suite utilizes local JSON mocks instead of live SharePoint lists to ensure fast, deterministic tests.
```bash
uv run pytest
```

### Running Locally
To run the Azure Functions host locally, install the [Azure Functions Core Tools](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local).
```bash
uv run func start
```

## CI/CD Deployment

The repository includes a GitHub Actions pipeline (`validator-ci-cd.yml`) that automatically runs tests on all PRs and deploys to Azure Functions on merges to `main`.

### Authentication (OIDC)
The pipeline uses OpenID Connect (OIDC) to securely authenticate to Azure without storing long-lived credentials. 

To configure this in your Azure tenant, execute the following Azure CLI commands to establish the federated identity credential:

```bash
# 1. Create an Entra ID App Registration
az ad app create --display-name "GitHub-Actions-Monoboard"

# 2. Create a Service Principal
az ad sp create --id <app-id>

# 3. Assign Contributor access to the Function App
az role assignment create --role contributor \
  --subscription <subscription-id> \
  --assignee-object-id <sp-object-id> \
  --scope /subscriptions/<subscription-id>/resourceGroups/<resource-group>/providers/Microsoft.Web/sites/monoboard-validator

# 4. Create the Federated Credential for the main branch
az ad app federated-credential create --id <app-id> --parameters '{"name":"github-main","issuer":"https://token.actions.githubusercontent.com","subject":"repo:your-org/monoboard.ai:ref:refs/heads/main","description":"Deploy from main","audiences":["api://AzureADTokenExchange"]}'
```

### Required GitHub Secrets
Navigate to **Settings > Secrets and variables > Actions** in the GitHub repository and configure the following:

- `AZURE_CLIENT_ID`: The Application (client) ID of the Entra ID app created above.
- `AZURE_TENANT_ID`: Your Azure Tenant ID.
- `AZURE_SUBSCRIPTION_ID`: The Azure Subscription ID where the Function App lives.
