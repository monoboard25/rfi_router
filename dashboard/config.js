window.MONOBOARD_CONFIG = {
  // Entra ID app registration — fill these in before deploying
  // Create at: portal.azure.com > Entra ID > App registrations > New
  // Redirect URI to add: https://<your-swa-name>.azurestaticapps.net/auth-callback
  clientId: "d6031e18-4470-4fe0-8c70-c615b7ced154",
  tenantId: "34203dd1-fd7b-44a0-bbcd-883962bdb191",

  // Storage account name (not a secret — safe to commit)
  storageAccount: "stmonoboard9476log",

  // Azure Function proxy base path (do not change)
  apiBase: "/api"
};
