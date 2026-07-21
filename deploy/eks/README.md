# EKS production deployment

The Helm chart deploys the same tested application images used by Docker Compose. It assumes the AWS foundation already exists; it does not silently create a VPC, database, or public endpoint.

For the Dev release on `macmtn-dev-cluster` (Entra auth disabled by design, host-less HTTP-only ALB), see `deploy/eks/dev-runbook.md` instead of the production steps below.

## Required AWS resources in `us-east-1`

1. An EKS cluster with the AWS Load Balancer Controller and metrics-server.
2. Two ECR repositories for the API and web images.
3. RDS PostgreSQL 16 with PostGIS enabled, reachable from the EKS node/pod security groups.
4. An ACM certificate and DNS record for the application host.
5. Two single-tenant Microsoft Entra app registrations (SPA and API), configured as described in `docs/entra-id.md`.
6. A Kubernetes secret named `photonops-runtime`, or External Secrets Operator plus a Secrets Manager JSON secret:

```json
{
  "database_url": "postgresql+asyncpg://USER:PASSWORD@RDS_HOST:5432/photonops",
  "bedrock_api_key": "AWS_BEDROCK_API_KEY_IF_ENABLED"
}
```

The database must use TLS in production. Add the required `ssl` query parameter for your RDS policy.

## Deploy

```bash
helm upgrade --install photonops ./deploy/helm/photon-ops-navigator \
  --namespace photonops --create-namespace \
  --set image.backend.repository=ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/photonops-api \
  --set image.frontend.repository=ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/photonops-web \
  --set image.backend.tag=GIT_SHA \
  --set image.frontend.tag=GIT_SHA \
  --set ingress.host=photonops.example.com \
  --set ingress.certificateArn=arn:aws:acm:us-east-1:ACCOUNT:certificate/ID \
  --set auth.tenantId=ENTRA_TENANT_GUID \
  --set auth.clientId=ENTRA_SPA_CLIENT_GUID \
  --set auth.apiClientId=ENTRA_API_CLIENT_GUID
```

The production chart fails closed with `auth.mode=entra`; all identifiers must be populated. Keep `seed.enabled=false` and switch `config.networkProvider` only after a real provider adapter is approved. For a private EKS demonstration using the deterministic network, set `seed.enabled=true`.

## Optional Amazon Bedrock Mantle summary

Set `config.aiProvider=bedrock_mantle` and supply an AWS-issued Bedrock API key. The adapter rejects non-AWS base URLs, uses `https://bedrock-mantle.us-east-1.api.aws/v1`, and sends `store=false`. The structured plan remains deterministic; Mantle only summarizes it.

## Production gates not hidden by the chart

- Enable RDS backups, deletion protection, Performance Insights, and encryption.
- Map Entra app roles to read-only/operator/admin authorization before adding write-capable workflows.
- Add CloudWatch logs/metrics, ALB access logs, WAF rules, and audit-event retention.
- Use private subnets and VPC endpoints/PrivateLink where organizational policy requires them.
- Replace the demo provider only from an approved VETRO/export schema; the included VETRO class is intentionally a stub.
