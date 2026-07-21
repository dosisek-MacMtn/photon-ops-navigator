# Dev EKS deployment runbook — macmtn-dev-cluster

Companion to `deploy/eks/README.md` (the production baseline). This is the
concrete, checked-in runbook for the Dev release on `macmtn-dev-cluster`
(AWS account `307187891552`, `us-east-1`), built for an exec demo with
Microsoft Entra ID intentionally disabled.

## 1. Auth is intentionally disabled — the non-negotiable check

CLAUDE.md states: "EKS/production authentication uses single-tenant
Microsoft Entra ID and must fail closed. Never weaken production auth to
make a deployment pass."

This Dev release does not violate that. Verified directly against
`backend/app/config.py`'s `validate_security_configuration`:

```python
if (
    self.environment == "production"
    and self.auth_mode == "disabled"
    and not self.allow_insecure_production_auth
):
    raise ValueError("AUTH_MODE=entra is required in production")
```

The fail-closed check keys **only** off `ENVIRONMENT == "production"`, not
"is this EKS" or any other condition. `values-dev.yaml` sets
`config.environment: dev` and `auth.mode: disabled`, which passes this check
cleanly with no override flag and no code changes. The Entra validation path
in `backend/app/auth.py` and the `auth.*` Helm values are untouched and
still fully wired — they just aren't exercised while `auth.mode: disabled`.

The frontend (`frontend/lib/auth.tsx`) fetches `/api/auth/config` at
startup and skips MSAL entirely when the API reports `{"mode": "disabled"}`
— no MSAL redirect URIs, tenant ID, or client ID need to exist for this
release to work.

**When presenting to the IT exec**: state plainly that Dev runs
unauthenticated by design, identical to the local Docker demo's anonymous
mode, and that production remains fail-closed on Entra with no override in
place anywhere in this repo.

## 2. Infrastructure prerequisite status (confirmed 2026-07-21)

| Prerequisite | Status |
|---|---|
| EKS cluster | `macmtn-dev-cluster` exists, EKS Auto Mode enabled |
| AWS Load Balancer Controller | Running, managed externally to the cluster |
| metrics-server / HPA metrics | Not confirmed independently of Auto Mode; HPA left enabled per decision below |
| ECR repositories `photonops-api` / `photonops-web` | Not confirmed to exist yet — create in account `307187891552` before first deploy |
| RDS PostgreSQL 16/PostGIS | Did not exist — provisioned by `deploy/terraform/eks-dev-rds/` (section 3) |
| ACM certificate / DNS host | None yet — Dev deliberately runs host-less/HTTP-only (section 4) |
| GitHub OIDC trust to an AWS role | Did not exist — must be created before `deploy-eks.yml` can run (section 5) |
| External Secrets Operator on the cluster | Not confirmed — required for the `externalSecrets.enabled: true` path in `values-dev.yaml`; verify with `kubectl get pods -n external-secrets` (or wherever it's installed) before first deploy. If absent, see the fallback in section 3. |

Confirm the two unconfirmed rows before the first real deploy attempt —
don't assume they're fine because the Terraform/Helm apply successfully.

## 3. Provision the Dev database

`deploy/terraform/eks-dev-rds/` provisions:

- An RDS PostgreSQL 16.4 instance (`db.t4g.micro`, single-AZ, 20GB gp3,
  `deletion_protection=false`, `skip_final_snapshot=true` — sized for a
  Dev/demo workload, not for anything holding data you can't regenerate from
  `app.seed`).
- A DB subnet group and security group, both derived automatically from
  `macmtn-dev-cluster`'s own VPC config via a Terraform data source — no
  manual VPC/subnet IDs needed.
- A Secrets Manager secret (`photonops/dev/runtime`) holding
  `{"database_url": "..."}` in the shape the chart expects.

This module has been syntax-checked (`python-hcl2` parses all four files
cleanly) but **not** run through `terraform validate`/`plan` against real
AWS state, and not applied — this sandboxed session has no `terraform`
binary and the org's egress policy blocks the hosts that distribute it.
Someone with cluster/AWS access needs to run:

```bash
cd deploy/terraform/eks-dev-rds
terraform init
terraform plan   # review instance size, subnet count, security group rule
terraform apply
terraform output runtime_secret_arn
```

PostGIS itself does not need a manual `CREATE EXTENSION` step — the
existing Alembic migration (`backend/alembic/versions/0001_initial_schema.py`)
already runs `CREATE EXTENSION IF NOT EXISTS postgis`, and the Helm chart's
`migration-job.yaml` hook runs `alembic upgrade head` automatically on every
install/upgrade.

**Secret delivery — confirm ESO first.** `values-dev.yaml` defaults to
`externalSecrets.enabled: true`, which requires the External Secrets
Operator already running on `macmtn-dev-cluster` with a `ClusterSecretStore`
named `aws-secrets-manager` (or update `externalSecrets.secretStoreName` to
match whatever it's actually called). If ESO is not installed:

```bash
helm upgrade --install photonops ./deploy/helm/photon-ops-navigator \
  -f deploy/helm/photon-ops-navigator/values-dev.yaml \
  --set externalSecrets.enabled=false ...

kubectl create secret generic photonops-runtime -n photonops \
  --from-literal=database_url="$(aws secretsmanager get-secret-value \
      --secret-id photonops/dev/runtime --query SecretString --output text \
      | python3 -c 'import json,sys; print(json.load(sys.stdin)["database_url"])')"
```

## 4. Ingress: host-less, HTTP-only for now

No Dev hostname or ACM certificate exists yet. `values-dev.yaml` sets
`ingress.host: ""` and `ingress.certificateArn: ""`. Two chart bugs were
fixed to make this work instead of silently assuming production-style TLS
always exists:

- `templates/ingress.yaml` previously hardcoded
  `alb.ingress.kubernetes.io/ssl-redirect: '443'` and listened on both
  `:80`/`:443` unconditionally — that redirects to a TLS listener that
  doesn't exist without a certificate. Both are now conditional on
  `ingress.certificateArn` being set.
- The `host` field on the Ingress rule is now conditional too; when unset,
  the rule matches any host, so the demo is reachable directly at the ALB's
  auto-assigned public DNS name.

Add a real `PHOTONOPS_HOST` (as a GitHub Dev environment variable) and
`ACM_CERTIFICATE_ARN` once a domain is ready — the workflow already reads
both and will switch to HTTPS with that host automatically (see section 6).

**CORS is a two-phase deploy** because the ALB's DNS name isn't known until
after the first apply. `.github/workflows/deploy-eks.yml` handles this
automatically: it deploys once with a bootstrap `config.allowedOrigin`,
polls `kubectl get ingress` for the assigned hostname, then runs a second
`helm upgrade --set config.allowedOrigin=...` to lock CORS to the real
origin before running the smoke test.

## 5. GitHub `Dev` environment setup (not yet done)

Create a GitHub Environment named `Dev` on this repo
(`dosisek-macmtn/photon-ops-navigator`) with these variables:

| Variable | Value |
|---|---|
| `AWS_DEPLOY_ROLE_ARN` | ARN of an AWS IAM role trusting this repo's GitHub OIDC provider, with permission to push to the two ECR repos and deploy to `macmtn-dev-cluster` (`eks:DescribeCluster` plus whatever RBAC the cluster's aws-auth/access entries grant that role) |
| `EKS_CLUSTER_NAME` | `macmtn-dev-cluster` |
| `PHOTONOPS_HOST` | leave unset for now (host-less Dev, section 4) |
| `ACM_CERTIFICATE_ARN` | leave unset for now |

`ENTRA_TENANT_ID` / `ENTRA_CLIENT_ID` / `ENTRA_API_CLIENT_ID` stay out of
this environment's variables entirely for now — auth is disabled for this
release (section 1) and the workflow never reads them. They remain in the
Helm chart's schema (`values.yaml` `auth.*`) for when Entra is enabled
later.

**GitHub OIDC trust does not exist yet.** This is an AWS-side change
(IAM OIDC identity provider for `token.actions.githubusercontent.com`, plus
a role with a trust policy scoped to this exact repo/branch) that has to be
created by whoever has IAM access in account `307187891552` — it isn't
something this repo's files can create. Per CLAUDE.md, do not copy trust
conditions from a different (e.g. eventual company-org) repository; scope
the trust policy's `sub` claim to
`repo:dosisek-macmtn/photon-ops-navigator:*` (or the specific branch/ref
this workflow runs from) for this repo as it exists today.

**Runner reachability is unresolved.** If `macmtn-dev-cluster`'s API server
turns out to be private-only, the `ubuntu-latest` GitHub-hosted runner in
`deploy-eks.yml` cannot reach it — swap `runs-on: ubuntu-latest` for a
company-approved self-hosted runner inside the VPC before the first real
run. Confirm public/private reachability before triggering the workflow.

## 6. Running the deploy

Once section 2, 3, and 5 are in place:

1. Push this branch (or merge to whatever branch the `Dev` environment's
   OIDC trust is scoped to).
2. Trigger **Actions → Deploy to EKS (Dev) → Run workflow**.
3. Watch the "Resolve public origin and lock CORS" step for the ALB
   hostname, and the smoke test step for `/health` and `/` passing.

## 7. Post-deploy validation

- `kubectl get pods -n photonops` — api/web Deployments healthy,
  readiness/liveness probes passing.
- Seed data loaded and labeled: query any service location/circuit and
  confirm names end in `(DEV)` — the seed job is
  `app.seed`, the same fictional dataset as the Docker demo.
- `kubectl get configmap photonops-config -n photonops -o yaml` shows
  `NETWORK_PROVIDER: "demo"` — confirm Dev is not pointed at a real VETRO
  endpoint (none exists yet; see `docs/vetro-integration.md`).
- Full demo workflow from `README.md` runs end-to-end against the ALB
  origin: intake → verified circuit → satellite route → OTDR correlation →
  outage impact → field plan → Photon Bench.

## 8. Explicitly out of scope

Per CLAUDE.md, this Dev deploy does not include: live VETRO integration,
CSV/XLSX import, the admin area, or any change to production Helm defaults
(Entra stays required and fail-closed there). These remain tracked under
CLAUDE.md's "Recommended next sequence."
