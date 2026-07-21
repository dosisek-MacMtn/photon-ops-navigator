# Photon-Ops Navigator

Photon-Ops Navigator is an AI-guided, circuit-aware fiber operations workspace. It gathers an operator’s narrative, resolves verified circuits through a provider-neutral network-data boundary, traces ordered plant routes on real satellite imagery, correlates OTDR distances, calculates outage impact, builds field action plans, and turns mapped distance into an optical loss budget in the integrated Photon Bench.

One codebase ships two deployment surfaces:

- **Docker demo:** Next.js, FastAPI, and deterministic PostgreSQL/PostGIS data with authentication disabled by default for a self-contained local demonstration.
- **EKS production:** the same images deployed with Helm in `us-east-1`, using RDS/PostGIS, ALB, Microsoft Entra ID, network policies, AWS-managed secrets, and optional Amazon Bedrock Mantle.

No VETRO endpoint or schema is invented. `backend/app/adapters/vetro.py` remains a documented stub behind the provider-neutral `NetworkDataProvider` contract.

## What is included

- Ordered-route OTDR correlation against mapped cable distance
- Graph-derived circuit and subscriber impact
- Guided investigation intake with optional AWS Bedrock Mantle intent extraction
- Provider-verified circuit, service-location, and approved splice-connectivity resolution before analysis begins
- Address-first residential service lookup with verified LCP, splitter, port, and premise lineage
- Real Esri World Imagery satellite basemap with MapLibre plant overlays
- Deterministic field action plans with optional AWS Bedrock Mantle summaries
- **Photon Bench:** circuit-linked OS2/OM4 loss budgeting, FOA typical and ANSI/TIA maximum allowances, event and splitter loss, predicted receive power, design margin, OTDR comparison, and per-segment loss contribution
- Microsoft Entra ID single-tenant sign-in using MSAL authorization code flow with PKCE
- API validation of token signature, issuer, tenant, audience, authorized client, expiry, and `access_as_user` scope
- Docker Compose demo and hardened Amazon EKS Helm deployment

## Run the Docker demo

Requirements: Docker Desktop with Compose.

```bash
docker compose up --build
```

Open [http://localhost:3000](http://localhost:3000). The development API documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

The database is only exposed to the Compose network. Startup applies Alembic migrations and idempotently seeds the fictional demo topology. To restore the known state:

```bash
docker compose exec api python -m app.reset
```

Stop with `docker compose down`. Add `-v` only when you intentionally want to delete the local database volume.

## Demo workflow

1. Start in **Navigator intake** and select the known prompt: `High loss on DXR-7001 at 18,420 ft from the OTDR launch`.
2. The demo parser structures the request and verifies `circuit-7001` against PostGIS. With `AI_PROVIDER=bedrock_mantle`, Amazon Bedrock performs the intent extraction instead.
3. Open the verified investigation. Residential records resolve by address, then carry their LCP/splitter-port lineage and linked engineering circuit into the satellite-map workspace.
4. Correlation lands on `Splice Closure SC-01` using accumulated route distance.
5. Review graph-derived downstream impact and generate the field action plan.
6. Open **Photon Bench**. The active circuit and route distance carry over automatically; switching to OM4 safely selects a compatible wavelength.

## Architecture

```text
Microsoft Entra ID ── PKCE/MSAL ──┐
                                  ▼
Next.js + Navigator + Satellite Map + Photon Bench ── Bearer token ── FastAPI
                                                       │
                            Bedrock intake / OTDR / graph impact / field plans
                                                       │
                                            NetworkDataProvider
                                              ├─ Demo: PostGIS
                                              └─ VETRO: approved-schema stub
```

The deterministic seed contains 91 assets, 76 cables, 50 service locations, 15 ordered circuits, and three known incidents. Residential service assets include serving LCP, splitter, splitter ratio, and port metadata. Core models include assets, cables, fiber strands, circuits, ordered path segments, service locations, OTDR tests, and OTDR events.

## Executive packet

- [Promotional flyer (PDF)](docs/executive/Photon-Ops-Navigator-Executive-Flyer.pdf)
- [Technical stack and architecture](docs/executive/TECH-STACK.md)
- [Security assessment](docs/security/SECURITY-ASSESSMENT.md)

See [ADR 0001](docs/adr/0001-two-deployment-surfaces-and-aws-ai.md) for the Docker/EKS decision and [ADR 0002](docs/adr/0002-photon-bench-and-entra-id.md) for the integrated Photon Bench and Entra ID decision.

## Microsoft Entra ID

Docker uses `AUTH_MODE=disabled` by default. EKS defaults to `AUTH_MODE=entra` and fails closed until the Entra identifiers are configured.

The implementation uses two single-tenant app registrations:

1. A **Photon-Ops SPA** registration with local and production SPA redirect URIs.
2. A **Photon-Ops API** registration exposing `api://<API_CLIENT_ID>/access_as_user`.

Grant the SPA delegated permission to that scope, then set:

```dotenv
AUTH_MODE=entra
ENTRA_TENANT_ID=<directory-tenant-guid>
ENTRA_CLIENT_ID=<spa-application-guid>
ENTRA_API_CLIENT_ID=<api-application-guid>
ENTRA_AUDIENCE=<api-application-guid>
ENTRA_REQUIRED_SCOPE=access_as_user
```

No client secret is used or stored by the browser application. Full registration and Helm instructions are in [docs/entra-id.md](docs/entra-id.md).

## Amazon Bedrock Mantle

AI is optional and never performs authoritative topology or optical analysis. When enabled, it extracts bounded investigation fields from the operator’s narrative and may add a non-authoritative executive summary:

```dotenv
AI_PROVIDER=bedrock_mantle
AWS_REGION=us-east-1
BEDROCK_MANTLE_BASE_URL=https://bedrock-mantle.us-east-1.api.aws/v1
BEDROCK_API_KEY=<Amazon Bedrock API key>
BEDROCK_MODEL=openai.gpt-oss-120b
```

The adapter rejects non-AWS Mantle URLs, sends `store=false`, validates the extracted fields, treats the incident narrative as untrusted data, and requires provider verification before the UI marks an input ready. Do not provide an OpenAI platform key; this application does not target OpenAI-hosted inference.

## VETRO FiberMap integration gate

The intake already calls the `NetworkDataProvider` contract, so enabling VETRO does not change the workflow or deterministic analysis. The production mapping is designed to include cables, strands, splice closures, trays, patch-panel ports, and ordered A-to-B splice relationships when the tenant's approved API profile exposes them. The checked-in VETRO implementation deliberately remains unavailable until the production owner supplies the customer-only API documentation, tenant base URL, read-scoped token mechanism, and approved response mappings. See [docs/vetro-integration.md](docs/vetro-integration.md).

## Validate

```bash
cd backend
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
ruff check .

cd ../frontend
npm ci
npm test
npm run typecheck
npm run build
```

For containers and deployment manifests:

```bash
docker compose config --quiet
helm lint --strict deploy/helm/photon-ops-navigator
```

## Production deployment

See [deploy/eks/README.md](deploy/eks/README.md). The chart defaults to `us-east-1`, two replicas per service, Entra authentication, non-root read-only containers, health probes, resource limits, HPAs, disruption budgets, network policies, ALB HTTPS redirect, optional WAF/External Secrets, and production seeding disabled.

See [SECURITY.md](SECURITY.md) for the security model and remaining production controls.
