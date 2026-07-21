# Photon-Ops Navigator — Claude Code Handoff

Photon-Ops Navigator is a runnable fiber-operations MVP with a Docker demo and an Amazon EKS deployment surface. It combines guided investigation intake, verified network lookups, circuit tracing on satellite imagery, OTDR correlation, outage impact, field plans, and the integrated Photon Bench optical calculator.

## Start here

1. Run `git status --short` and preserve unrelated/user-owned changes.
2. Read `README.md`, `SECURITY.md`, and the specific document linked below for the area being changed.
3. Verify claims against the code. Some documents describe approved future direction as well as implemented behavior.
4. Keep Docker demo and EKS behavior compatible unless the user explicitly narrows the scope.

## Non-negotiable product and security decisions

- The product name is **Photon-Ops Navigator**. Do not reintroduce “FiberOps Copilot,” “Photon-Ops CoPilot,” or Microsoft Copilot terminology.
- **Photon Bench** is part of the Navigator product, not a separate application.
- Ship one codebase as two deployment surfaces: Docker Compose for demos and Helm on EKS for Dev/Prod.
- AWS region is `us-east-1`.
- If AI is enabled, use **Amazon Bedrock Mantle** only. Deterministic topology, distance, outage, and optical calculations remain authoritative; LLM output is bounded, optional, and non-authoritative.
- EKS/production authentication uses single-tenant Microsoft Entra ID and must fail closed. Never weaken production auth to make a deployment pass.
- Never invent VETRO endpoints, credentials, fields, or splice semantics. The real adapter remains gated on approved tenant documentation, a sample/export schema, and contract fixtures.
- Seeded service locations and addresses are fictional and end in `(DEV)`. Keep that label on demo data; do not append it to real provider/imported records.
- The map uses Esri World Imagery through MapLibre. Preserve attribution, the restricted tile host, and safe DOM-based popups.
- Never commit tokens, passwords, customer network data, VETRO exports, Entra secrets, AWS credentials, or `.env` files.

## Implemented architecture

```text
Operator
  -> Next.js 16 / React 19 / TypeScript UI
       -> Navigator intake and operations console
       -> MapLibre + Esri World Imagery
       -> Photon Bench optical calculator
       -> MSAL Entra PKCE authentication
  -> FastAPI / Python 3.12 API
       -> deterministic investigation and optical workflows
       -> optional Bedrock Mantle intake/summary adapter
       -> NetworkDataProvider boundary
            -> demo PostGIS provider (implemented)
            -> VETRO provider (intentional stub)
  -> PostgreSQL 16 + PostGIS
```

Key directories:

- `frontend/app/` — Next.js entry point, layout, providers, and global styling.
- `frontend/components/` — guided intake, operations console, map, and Photon Bench UI.
- `frontend/lib/` — API client, MSAL auth, and optical calculations/tests.
- `backend/app/api/routes.py` — authenticated HTTP API surface.
- `backend/app/services/` — Navigator parsing, OTDR analysis, topology, reports, and AI boundary.
- `backend/app/adapters/` — provider-neutral contract, demo PostGIS provider, and VETRO stub.
- `backend/app/models/entities.py` — canonical MVP persistence model.
- `backend/app/demo_data.py` and `backend/app/seed.py` — deterministic fictional topology.
- `deploy/helm/photon-ops-navigator/` — EKS Helm chart.
- `.github/workflows/ci.yml` — tests, audits, secret/config scans, builds, and image scans.
- `.github/workflows/deploy-eks.yml` — manually dispatched EKS image build/push/deploy workflow.

The current database model supports PostGIS `POINT` assets and `LINESTRING` cables (SRID 4326), strands, service locations, circuits, ordered circuit path segments, OTDR tests, and OTDR events. Residential demo paths include serving LCP/splitter/port lineage in asset metadata; an explicit normalized splice/closure/tray/port graph is not implemented yet.

## Commands

Run these from the repository root unless a command starts with `cd`.

```bash
# Docker demo
docker compose up -d --build
docker compose ps
curl --fail http://localhost:8000/health
curl --fail http://localhost:3000/

# Restore the deterministic demo data
docker compose exec -T api python -m app.reset

# Stop without deleting the database volume
docker compose down

# Backend validation (after creating backend/.venv per README.md)
(cd backend && .venv/bin/python -m ruff check app tests)
(cd backend && .venv/bin/python -m pytest -q)

# Frontend validation
(cd frontend && npm ci)
(cd frontend && npm test)
(cd frontend && npm run typecheck)
(cd frontend && npm run build)

# Compose and Helm validation
docker compose config --quiet
helm lint --strict deploy/helm/photon-ops-navigator
```

If Helm is unavailable locally, validate with the pinned container pattern:

```bash
docker run --rm -v "$PWD:/work" -w /work alpine/helm:3.19.0 \
  lint deploy/helm/photon-ops-navigator --strict
```

Local URLs are `http://localhost:3000` for the UI and `http://localhost:8000/docs` for development API docs. Do not use `docker compose down -v` unless deleting the local PostGIS volume is intentional.

## Environment and behavior

- Docker defaults: `NETWORK_PROVIDER=demo`, `AUTH_MODE=disabled`, and `AI_PROVIDER=deterministic`.
- EKS chart defaults: Entra auth enabled, two API and web replicas, network policies, HPA/PDB, non-root read-only containers, ALB ingress, and `seed.enabled=false`.
- The API rejects disabled authentication when `ENVIRONMENT=production`, unless the explicit insecure override is set. Do not use that override in EKS.
- Bedrock Mantle uses `https://bedrock-mantle.us-east-1.api.aws/v1`, an AWS-issued key, `store=false`, and model `openai.gpt-oss-120b` by default. The model name does not mean OpenAI-hosted inference.
- CORS must contain the exact UI origin; wildcards and origins containing paths are rejected.
- Docker’s database password is deliberately local-only. EKS receives `database_url` and optional `bedrock_api_key` from `photonops-runtime` or External Secrets.

Copy configuration from `.env.example`; do not put real values in tracked files. See `docs/entra-id.md` for the two Entra app registrations and API `access_as_user` scope.

## Current functional state

Implemented and tested:

- Guided operator narrative intake with deterministic parsing and optional Bedrock extraction.
- Provider verification before the UI marks a circuit/service location ready.
- Circuit-ID and address-first residential lookup.
- Ordered route tracing, OTDR distance correlation, graph-derived outage impact, and field action plans.
- Satellite basemap with plant overlays.
- Photon Bench OS2/OM4 calculations, safe fiber/wavelength switching, event/splitter loss, power/margin, and route-linked segment contributions.
- Entra SPA PKCE login and API validation of signature, tenant, issuer, audience, authorized client, expiry, and delegated scope.
- Docker demo, EKS Helm manifests, CI, dependency/security scans, and fictional `(DEV)` seed data.

Not implemented; do not claim otherwise:

- Live VETRO API access.
- CSV/XLSX VETRO import or an admin import UI.
- Normalized splice enclosures, trays/cassettes, patch-panel ports, strand endpoints, and A-to-B connection records.
- Admin management for non-Entra users, application role assignment, or role-based endpoint enforcement. Tokens expose roles/scopes, but the MVP currently enforces the delegated scope rather than operator/read-only/admin policies.
- AWS infrastructure provisioning. The chart assumes EKS, ECR, RDS/PostGIS, ALB Controller, metrics-server, ACM/DNS, secrets, networking, and identity foundations already exist.
- A repository-tracked Dev-specific Helm values file and complete Dev deployment runbook.

## VETRO and file-import direction

Read `docs/vetro-integration.md` before touching provider integration.

- API and CSV/XLSX ingestion should feed the same canonical validation and persistence pipeline; PostGIS can store normalized geometry from either source.
- Stage imports before publish. Validate required identifiers, geometry/SRID, referential integrity, ordered paths, strand ranges, duplicate/source IDs, and connection endpoints.
- Publish transactionally and record import version, source, checksum, counts, validation errors, actor, and timestamp. Design for safe retry/idempotency and rollback to the last accepted import.
- Preserve provider source/audit IDs on every normalized record. Unknown fields stay unknown; never infer splice connectivity.
- Obtain official tenant API documentation or representative redacted CSV/XLSX exports before defining mappings.
- Begin read-only: address/service-location lookup, circuit path, asset lookup, and splice-connectivity retrieval when the approved source exposes it.

## Admin-area direction

The requested admin area is planned, not built. Its intended scope is:

- staged CSV/XLSX upload, mapping, validation preview, publish, history, and rollback;
- provider connection/status controls without exposing credentials;
- non-Entra user lifecycle only if the organization explicitly approves a second identity source;
- application roles/permissions mapped to Entra groups/app roles where possible;
- immutable audit events for access and data changes.

Do not add password authentication casually. Resolve identity ownership, password/MFA/reset policy, and production authorization roles with the company security team first.

## EKS Dev handoff

The repository is EKS-oriented but not a turnkey infrastructure stack. Before the first Dev deployment:

1. Confirm EKS access, AWS Load Balancer Controller, metrics-server, ECR repositories `photonops-api` and `photonops-web`, RDS PostgreSQL 16/PostGIS, TLS, ACM/DNS, and the runtime secret.
2. Create `deploy/helm/photon-ops-navigator/values-dev.yaml` with the actual host/origin, Dev sizing, approved secret mechanism, `config.networkProvider=demo`, and `seed.enabled=true` for the fictional Dev dataset.
3. Update `.github/workflows/deploy-eks.yml` to consume the Dev values file and set the exact allowed origin. Keep `seed.enabled=false` for production.
4. Configure the GitHub `Dev` environment variables: `AWS_DEPLOY_ROLE_ARN`, `EKS_CLUSTER_NAME`, `PHOTONOPS_HOST`, `ACM_CERTIFICATE_ARN`, `ENTRA_TENANT_ID`, `ENTRA_CLIENT_ID`, and `ENTRA_API_CLIENT_ID`.
5. Configure GitHub OIDC trust and EKS access for the **company repository identity** after that repository exists. Do not copy immutable repository IDs or trust conditions from the personal repository.
6. If the EKS API is private-only, use a company-approved self-hosted runner inside the VPC; a GitHub-hosted runner cannot reach it.

Use `deploy/eks/README.md` as the checked-in baseline. Entra redirect URIs and CORS must match the final HTTPS hostname exactly.

## GitHub and local handoff

- The current `origin` is the user’s private personal repository. The user will upload/import the local repository into the company GitHub organization.
- Do not transfer the repository, replace `origin`, push to a company organization, or change AWS/GitHub trust without an explicit company repository target and authorization.
- After company upload, treat the company repository as the deployment source, recreate GitHub environments/branch protection, and update AWS OIDC trust for its actual organization, repository, and immutable IDs.
- If an untracked `README 2.md` is present in this local clone, it belongs to the user. Do not stage, overwrite, or remove it unless asked.

## Change and validation expectations

- Preserve unrelated dirty-worktree changes; stage only files belonging to the requested change.
- Use Alembic for schema changes and add migration/contract tests.
- Add backend tests for auth/provider/analysis behavior and frontend tests for optical edge cases and interactive regressions.
- For UI changes, validate responsive behavior, keyboard/focus states, contrast, and loading/error/empty states while retaining the gaiia-inspired dark operational feel without copying proprietary assets.
- Run the narrowest relevant tests during development and the full backend/frontend validation before handoff. For deployment changes, also run Compose config and strict Helm lint.
- Update security and architecture documentation when a boundary, dependency, deployment assumption, or accepted risk changes.

## Recommended next sequence

1. Add and validate the Dev Helm values file plus a repository Dev EKS runbook.
2. Make the deploy workflow consume those values and verify a Dev release in `us-east-1`.
3. Complete company GitHub environment, branch protection, OIDC, and EKS access configuration after the user provides the target.
4. Obtain approved VETRO API documentation or redacted representative exports.
5. Design and migrate the canonical import/splice graph, then build staged admin import workflows and role enforcement.

Relevant decisions and evidence: `docs/adr/`, `docs/vetro-integration.md`, `docs/entra-id.md`, `docs/security/SECURITY-ASSESSMENT.md`, and `docs/executive/TECH-STACK.md`.
