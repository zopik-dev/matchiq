# MatchIQ Azure deployment (PowerShell mirror of deploy.sh).
# Prerequisites: Azure CLI logged in (`az login`), Docker Desktop running.
# Secrets come from YOUR environment, never from the repo.
# Usage: .\infra\azure\deploy.ps1 [-ResourceGroup matchiq-rg] [-Location westeurope] [-Registry matchiqacr]
param(
  [string]$ResourceGroup = "matchiq-rg",
  [string]$Location = "westeurope",
  [string]$Registry = "matchiqacr",
  [string]$Tag = "latest"
)
$ErrorActionPreference = "Stop"

Write-Output "==> resource group + environment"
az group create -n $ResourceGroup -l $Location -o none
az extension add -n containerapp --upgrade -y -o none 2>$null
az provider register -n Microsoft.App -o none
az provider register -n Microsoft.OperationalInsights -o none
az acr create -g $ResourceGroup -n $Registry --sku Basic -o none 2>$null
az acr login -n $Registry -o none
az containerapp env create -g $ResourceGroup -n matchiq-env -l $Location -o none 2>$null

Write-Output "==> Cosmos DB (serverless, SQL API)"
$CosmosAccount = "matchiq-cosmos-$(Get-Random -Minimum 1000 -Maximum 9999)"
az cosmosdb create -g $ResourceGroup -n $CosmosAccount --kind GlobalDocumentDB `
  --capabilities EnableServerless -o none
az cosmosdb sql database create -g $ResourceGroup -a $CosmosAccount -n matchiq -o none
az cosmosdb sql container create -g $ResourceGroup -a $CosmosAccount -d matchiq `
  -n matches --partition-key-path "/id" -o none
$CosmosEndpoint = "https://$CosmosAccount.documents.azure.com:443/"
$CosmosKey = if ($env:MATCHIQ_COSMOS_KEY) { $env:MATCHIQ_COSMOS_KEY } else {
  az cosmosdb keys list -g $ResourceGroup -n $CosmosAccount --query primaryMasterKey -o tsv
}

Write-Output "==> build + push images"
$RegUrl = "$Registry.azurecr.io"
docker build -f infra/backend.Dockerfile -t "$RegUrl/matchiq-backend:$Tag" .
docker push "$RegUrl/matchiq-backend:$Tag"

Write-Output "==> backend app (scale to zero)"
$Secrets = @("cosmos-key=$CosmosKey")
$BackendEnv = @("MATCHIQ_ENV=azure")
if ($env:MATCHIQ_AZURE_API_KEY) { $Secrets += "azure-key=$env:MATCHIQ_AZURE_API_KEY" }
az containerapp create -g $ResourceGroup -n matchiq-backend --environment matchiq-env `
  --image "$RegUrl/matchiq-backend:$Tag" --registry-server $RegUrl `
  --target-port 8000 --ingress external `
  --min-replicas 0 --max-replicas 2 --cpu 0.5 --memory 1Gi `
  --env-vars $BackendEnv --secrets $Secrets -o none
$UpdateEnv = @("MATCHIQ_COSMOS_ENDPOINT=$CosmosEndpoint", "MATCHIQ_COSMOS_KEY=secretref:cosmos-key")
if ($env:MATCHIQ_AZURE_ENDPOINT) { $UpdateEnv += "MATCHIQ_AZURE_ENDPOINT=$env:MATCHIQ_AZURE_ENDPOINT" }
if ($env:MATCHIQ_AZURE_DEPLOYMENT) { $UpdateEnv += "MATCHIQ_AZURE_DEPLOYMENT=$env:MATCHIQ_AZURE_DEPLOYMENT" }
if ($env:MATCHIQ_AZURE_API_KEY) { $UpdateEnv += "MATCHIQ_AZURE_API_KEY=secretref:azure-key" }
az containerapp update -g $ResourceGroup -n matchiq-backend --set-env-vars $UpdateEnv -o none
$BackendFqdn = az containerapp show -g $ResourceGroup -n matchiq-backend `
  --query properties.configuration.ingress.fqdn -o tsv

Write-Output "==> frontend app (API baked to backend FQDN)"
docker build -f infra/frontend.Dockerfile `
  --build-arg "VITE_API_URL=https://$BackendFqdn" `
  -t "$RegUrl/matchiq-frontend:$Tag" .
docker push "$RegUrl/matchiq-frontend:$Tag"
az containerapp create -g $ResourceGroup -n matchiq-frontend --environment matchiq-env `
  --image "$RegUrl/matchiq-frontend:$Tag" --registry-server $RegUrl `
  --target-port 80 --ingress external `
  --min-replicas 0 --max-replicas 2 --cpu 0.25 --memory 0.5Gi -o none
$FrontendFqdn = az containerapp show -g $ResourceGroup -n matchiq-frontend `
  --query properties.configuration.ingress.fqdn -o tsv

Write-Output "==> updating backend CORS for the frontend origin"
az containerapp update -g $ResourceGroup -n matchiq-backend `
  --set-env-vars "MATCHIQ_CORS_ORIGINS=https://$FrontendFqdn" -o none

Write-Output "DONE. Frontend: https://$FrontendFqdn  Backend: https://$BackendFqdn"
