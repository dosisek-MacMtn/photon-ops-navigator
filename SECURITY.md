# Security policy and deployment model

## Report a vulnerability

Do not open an issue containing exploit details, credentials, network topology, or customer data. Contact the repository owner through an approved private channel or open a private GitHub security advisory.

## Security controls in this MVP

- Microsoft Entra ID single-tenant authentication for the browser and API
- Tenant, issuer, signature, audience, authorized-client, lifetime, and scope validation
- No client secret in the SPA
- Explicit CORS origins and bearer tokens; credentialed cross-origin requests are disabled
- Browser security headers, frame denial, restrictive permissions policy, and CSP
- API responses marked `no-store` with defensive headers
- Non-root containers with dropped capabilities and read-only filesystems
- EKS pod security contexts, network policies, resource limits, health checks, PDBs, and optional WAF
- RDS credentials and optional Bedrock keys supplied through Kubernetes Secrets or External Secrets
- Database not published to the host in Docker Compose
- Amazon Bedrock Mantle is optional, AWS-only, non-authoritative, and configured with `store=false`
- Demo topology is fictional and deterministic

## Production responsibilities

Before production use, the platform owner must provide private EKS/RDS networking, TLS-only RDS connections, encryption and backups, ALB access logs, WAF rules, centralized application/audit logs, alerting, secret rotation, image signing/scanning, dependency monitoring, and an approved real network-data adapter. Role-based authorization beyond the initial `access_as_user` permission should be mapped to organizational operator/read-only/admin roles before write-capable workflows are added.

The Docker profile is a local demonstration surface. Its known local-only database password must never be promoted into EKS, RDS, or a shared environment.

The dated application-assessment evidence and accepted constraints are recorded in [docs/security/SECURITY-ASSESSMENT.md](docs/security/SECURITY-ASSESSMENT.md).
