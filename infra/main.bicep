targetScope = 'resourceGroup'

@description('Azure region for all resources.')
param location string = 'eastus'

@description('Globally-unique storage account name (3-24 lowercase alphanumeric).')
param storageAccountName string = 'stmonoboardprodlog'

@description('Python runtime version for the Function Apps.')
param pythonVersion string = '3.11'

@description('Names of the five Function Apps.')
param functionAppNames array = [
  'monoboard9476-validator'
  'monoboard9476-rfi-router'
  'monoboard9476-change-order'
  'monoboard9476-daily-report'
  'monoboard9476-ceo-agent'
  'monoboard9476-safety-monitor'
  'monoboard9476-bid-assist'
  'monoboard9476-onboarding-agent'
]

var planName = 'asp-monoboard9476-prod'
var aiName = 'appi-monoboard9476-prod'
var tableName = 'agentruns'

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}

resource tableSvc 'Microsoft.Storage/storageAccounts/tableServices@2023-05-01' = {
  name: 'default'
  parent: storage
}

resource agentrunsTable 'Microsoft.Storage/storageAccounts/tableServices/tables@2023-05-01' = {
  name: tableName
  parent: tableSvc
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: aiName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

resource plan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: planName
  location: location
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  kind: 'linux'
  properties: {
    reserved: true
  }
}

var storageConn = 'DefaultEndpointsProtocol=https;AccountName=${storage.name};AccountKey=${storage.listKeys().keys[0].value};EndpointSuffix=${environment().suffixes.storage}'

resource functionApps 'Microsoft.Web/sites@2023-12-01' = [for name in functionAppNames: {
  name: name
  location: location
  kind: 'functionapp,linux'
  identity: { type: 'SystemAssigned' }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'Python|${pythonVersion}'
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      appSettings: [
        { name: 'AzureWebJobsStorage', value: storageConn }
        { name: 'WEBSITE_CONTENTAZUREFILECONNECTIONSTRING', value: storageConn }
        { name: 'WEBSITE_CONTENTSHARE', value: toLower(name) }
        { name: 'FUNCTIONS_EXTENSION_VERSION', value: '~4' }
        { name: 'FUNCTIONS_WORKER_RUNTIME', value: 'python' }
        { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsights.properties.ConnectionString }
      ]
    }
  }
}]

output storageAccountId string = storage.id
output storageConnectionString string = storageConn
output appInsightsConnectionString string = appInsights.properties.ConnectionString
output functionAppHostnames array = [for (name, i) in functionAppNames: functionApps[i].properties.defaultHostName]
