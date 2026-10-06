# Azure integration guide: Foundry, Cosmos DB, secrets

MatchIQ runs fully offline (MockLLM + in-memory store). This page wires the
two optional Azure integrations. Nothing here requires committing secrets:
every credential travels as an environment variable, a Container Apps secret,
or a Managed Identity — never in the repo (`.env` is git-ignored).

## 1. Microsoft Foundry models (`AzureFoundryLLM`)

`backend/app/llm/azure.py` speaks the Azure OpenAI chat-completions API,
which covers both Azure OpenAI and Microsoft Foundry model deployments.

1. In the [Foundry portal](https://ai.azure.com), deploy a chat model
   (e.g. GPT-4o-mini) and note the **endpoint**, **deployment name** and key.
2. Local run — export (PowerShell shown) and restart the backend:
   ```powershell
   $env:MATCHIQ_AZURE_ENDPOINT = "https://<resource>.openai.azure.com"
   $env:MATCHIQ_AZURE_API_KEY = "<key>"
   $env:MATCHIQ_AZURE_DEPLOYMENT = "<deployment>"
   uvicorn app.main:app --port 8000  # from backend/
   ```
3. CLI check: `python -m app.agents run --llm azure`. Without credentials the
   client reports `available() == False` and the pipeline falls back to
   MockLLM — the demo never breaks for missing keys.
4. Azure hosting: `deploy.sh`/`deploy.ps1` reads the same three variables from
   your shell and stores the key as a Container Apps secret
   (`azure-key`), referenced via `secretref`. Rotate with
   `az containerapp secret set`.

Grounding still applies: every Azure-generated line passes the evidence
validator (`app/llm/grounding.py`); violations fall back to templates.

### Managed Identity (keyless, recommended for production)

1. Enable a system-assigned identity:
   `az containerapp identity assign -g <rg> -n matchiq-backend --system-assigned`
2. Grant it `Cognitive Services OpenAI User` on the Foundry resource.
3. The stock `AzureFoundryLLM` uses key auth; for keyless auth, fetch an AAD
   token from IMDS and send `Authorization: Bearer` instead of `api-key`
   (same pattern as `fetch_managed_identity_token()` in
   `backend/app/store/cosmos.py`).

## 2. Cosmos DB match state (`CosmosStore`)

`backend/app/store/cosmos.py` implements the existing `MatchStore` interface
over the Cosmos DB SQL API with **zero new dependencies** (stdlib REST +
HMAC signing). `build_store()` returns it automatically when
`MATCHIQ_COSMOS_ENDPOINT` (+ key or Managed Identity) is set, otherwise the
in-memory store — the API code path is identical either way.

Local run against Cosmos:
```powershell
$env:MATCHIQ_COSMOS_ENDPOINT = "https://<account>.documents.azure.com:443/"
$env:MATCHIQ_COSMOS_KEY = "<primary key>"
```
`deploy.sh`/`deploy.ps1` provisions a **serverless** account plus the
`matchiq` database / `matches` container (partition key `/id`) and injects
both values. Keyless alternative: set `MATCHIQ_USE_MANAGED_IDENTITY=1`,
enable the app identity, and grant it Cosmos DB Built-in Data Contributor.

## 3. Cost control

- Both Container Apps deploy with `--min-replicas 0` (scale to zero when
  idle) and small sizes (backend 0.5 CPU/1 Gi, frontend 0.25 CPU/0.5 Gi).
- Cosmos DB uses the serverless capability (request-unit billing, no
  provisioned throughput).
- The demo dataset ships inside the backend image; no storage account needed.
