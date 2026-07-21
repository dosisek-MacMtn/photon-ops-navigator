# Photon-Ops Navigator — Security Assessment

**Assessment date:** 2026-07-21
**Scope:** application source, Python and npm dependencies, authentication boundary, Docker demo, Helm/EKS manifests, and repository secret exposure

## Executive result

No open critical, high, or medium source-code finding was identified in the MVP at handoff. Dependency audits report no known Python or npm vulnerability after remediation. The production profile fails closed unless Microsoft Entra ID is fully configured.

This is an application assessment, not a penetration test or authorization to process production network data. The production owner must still complete cloud-account controls, environment-specific threat modeling, external testing, and operational approvals.

## Checks performed

| Check | Result |
|---|---|
| Python tests | 9 passed |
| TypeScript optical-model tests | 4 passed, including incompatible OM4 wavelength regression |
| Python lint | Passed |
| TypeScript type check and Next.js production build | Passed |
| `pip-audit` against the active application environment | No known vulnerabilities |
| `npm audit` | 0 vulnerabilities |
| Bandit static analysis of `backend/app` | 0 findings |
| Trivy scan of final web and API images | 0 high or critical vulnerabilities |
| Ruflo full application scan | 0 critical, high, medium, or low findings |
| Repository credential-pattern review | No private keys, AWS access keys, or client secrets found |
| Docker Compose validation and live smoke test | Passed; API healthy and database not host-published |
| Helm strict lint and rendered-manifest parse | Passed |

## Findings remediated during the review

- Replaced an affected Starlette/FastAPI dependency set and pinned the remediated runtime versions.
- Moved test and audit tooling out of the production Python dependency set and upgraded affected development packages.
- Upgraded the image-build `pip` version.
- Removed the unused npm CLI and its dependency tree from the final web runtime image after container scanning identified affected CLI-only packages in the base image.
- Added strict Entra token validation for RSA signature, tenant, issuer, API audience, authorized SPA client, lifetime, and delegated scope.
- Removed host publication of PostgreSQL and hardened demo containers with non-root users, dropped capabilities, read-only filesystems, and temporary writable mounts.
- Added EKS network policies, restricted service-account token mounting, pod security contexts, resource limits, health probes, disruption budgets, and optional ALB/WAF integration.
- Added explicit CORS policy and defensive browser/API headers.
- Replaced HTML-string map popups with DOM nodes and `textContent`, preventing provider-sourced asset names from becoming executable markup.
- Restricted satellite tile access to the explicit Esri host in the content-security policy and preserved map attribution.
- Bounded Navigator message sizes and LLM output fields, treats incident text as untrusted data, disables response storage, and requires a provider match before a circuit can be marked verified.

## Accepted constraints and production gates

- The Next.js content-security policy permits inline bootstrap scripts required by the framework build. It still denies objects and framing, restricts origins, and should be revisited if a nonce-based deployment pattern is introduced.
- Esri World Imagery is an external production dependency. Procurement and legal owners must approve provider terms, attribution, availability, and any desired enterprise tile service before launch.
- The Docker profile contains a documented local-only database password and disables authentication by default for a self-contained laptop demo. It must never be reused in production.
- Initial authorization grants the `access_as_user` delegated permission. Organization-specific operator, read-only, and administrator roles must be defined before write-capable workflows are enabled.
- Production requires private EKS/RDS networking, TLS to RDS, encryption and backups, real secret management and rotation, image signing, centralized logs and alerts, AWS WAF rules, and an approved network-data adapter.
- A qualified third party should perform an environment-specific penetration test before production approval.

## Entra ID boundary

The browser uses authorization code flow with PKCE and stores tokens in session storage. The SPA has no client secret. The API accepts only a tenant-specific, API-audience token issued for the configured SPA client with the required delegated scope. Production startup is rejected when this configuration is absent or when authentication is disabled.
