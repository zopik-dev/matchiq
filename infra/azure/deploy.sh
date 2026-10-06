#!/usr/bin/env bash
# MatchIQ Azure deployment: Container Apps (scale-to-zero) + Cosmos DB (serverless).
# Prerequisites: Azure CLI logged in (`az login`), Docker daemon running.
# Secrets come from YOUR environment, never from the repo:
#   MATCHIQ_AZURE_API_KEY, MATCHIQ_COSMOS_KEY (or leave Cosmos to be created here)
# Usage: ./infra/azure/deploy.sh [resource-group] [location] [registry]
set -euo pipefail

RG="${1:-matchiq-rg}"
LOCATION="${2:-westeurope}"
REGISTRY="${3:-matchiqacr}"
ENV_NAME="matchiq-env"
COSMOS_ACCOUNT="matchiq-cosmos-$RANDOM"
TAG="${TAG:-latest}"

echo "==> resource group + environment"
az group create -n "$RG" -l "$LOCATION" -o none
az extension add -n containerapp --upgrade -y -o none 2>/dev/null || true
az provider register -n Microsoft.App -o none
az provider register -n Microsoft.OperationalInsights -o none
az acr create -g "$RG" -n "$REGISTRY" --sku Basic -o none 2>/dev/null || true
az acr login -n "$REGISTRY" -o none
az containerapp env create -g "$RG" -n "$ENV_NAME" -l "$LOCATION" -o none 2>/dev/null || true

echo "==> Cosmos DB (serverless, SQL API)"
az cosmosdb create -g "$RG" -n "$COSMOS_ACCOUNT" --kind GlobalDocumentDB \
  --capabilities EnableServerless -o none
az cosmosdb sql database create -g "$RG" -a "$COSMOS_ACCOUNT" -n matchiq -o none
az cosmosdb sql container create -g "$RG" -a "$COSMOS_ACCOUNT" -d matchiq \
  -n matches --partition-key-path "/id" -o none
COSMOS_ENDPOINT="https://${COSMOS_ACCOUNT}.documents.azure.com:443/"
COSMOS_KEY="${MATCHIQ_COSMOS_KEY:-$(az cosmosdb keys list -g "$RG" -n "$COSMOS_ACCOUNT" --query primaryMasterKey -o tsv)}"

echo "==> build + push images"
REG_URL="${REGISTRY}.azurecr.io"
docker build -f infra/backend.Dockerfile -t "$REG_URL/matchiq-backend:$TAG" .
docker push "$REG_URL/matchiq-backend:$TAG"

echo "==> backend app (scale to zero)"
az containerapp create -g "$RG" -n matchiq-backend --environment "$ENV_NAME" \
  --image "$REG_URL/matchiq-backend:$TAG" --registry-server "$REG_URL" \
  --target-port 8000 --ingress external \
  --min-replicas 0 --max-replicas 2 --cpu 0.5 --memory 1Gi \
  --env-vars MATCHIQ_ENV=azure \
  --secrets cosmos-key="$COSMOS_KEY" ${MATCHIQ_AZURE_API_KEY:+azure-key="$MATCHIQ_AZURE_API_KEY"} \
  -o none
az containerapp update -g "$RG" -n matchiq-backend \
  --set-env-vars "MATCHIQ_COSMOS_ENDPOINT=$COSMOS_ENDPOINT" \
    "MATCHIQ_COSMOS_KEY=secretref:cosmos-key" \
    ${MATCHIQ_AZURE_ENDPOINT:+MATCHIQ_AZURE_ENDPOINT="$MATCHIQ_AZURE_ENDPOINT"} \
    ${MATCHIQ_AZURE_DEPLOYMENT:+MATCHIQ_AZURE_DEPLOYMENT="$MATCHIQ_AZURE_DEPLOYMENT"} \
    ${MATCHIQ_AZURE_API_KEY:+MATCHIQ_AZURE_API_KEY=secretref:azure-key} \
  -o none
BACKEND_FQDN=$(az containerapp show -g "$RG" -n matchiq-backend \
  --query properties.configuration.ingress.fqdn -o tsv)

echo "==> frontend app (API baked to backend FQDN)"
docker build -f infra/frontend.Dockerfile \
  --build-arg "VITE_API_URL=https://$BACKEND_FQDN" \
  -t "$REG_URL/matchiq-frontend:$TAG" .
docker push "$REG_URL/matchiq-frontend:$TAG"
az containerapp create -g "$RG" -n matchiq-frontend --environment "$ENV_NAME" \
  --image "$REG_URL/matchiq-frontend:$TAG" --registry-server "$REG_URL" \
  --target-port 80 --ingress external \
  --min-replicas 0 --max-replicas 2 --cpu 0.25 --memory 0.5Gi -o none
FRONTEND_FQDN=$(az containerapp show -g "$RG" -n matchiq-frontend \
  --query properties.configuration.ingress.fqdn -o tsv)

echo "==> updating backend CORS for the frontend origin"
az containerapp update -g "$RG" -n matchiq-backend \
  --set-env-vars "MATCHIQ_CORS_ORIGINS=https://$FRONTEND_FQDN" -o none

echo "DONE. Frontend: https://$FRONTEND_FQDN  Backend: https://$BACKEND_FQDN"
