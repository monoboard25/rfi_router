#!/usr/bin/env bash
set -euo pipefail

RG="${RG:-agent-monoboard-prod}"
LOC="${LOC:-eastus}"
SUB="${SUB:-}"

if [[ -n "$SUB" ]]; then
  az account set --subscription "$SUB"
fi

az group create --name "$RG" --location "$LOC" >/dev/null

az deployment group create \
  --resource-group "$RG" \
  --template-file "$(dirname "$0")/main.bicep" \
  --parameters "@$(dirname "$0")/main.parameters.json"
