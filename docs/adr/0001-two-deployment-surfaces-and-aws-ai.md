# ADR-0001: One application with Docker demo and EKS production surfaces

**Status:** Accepted
**Date:** 2026-07-20
**Decider:** Product owner

## Context

Photon-Ops Navigator must run as a self-contained local demo without VETRO access and also have a credible AWS production deployment. The domain behavior must remain identical across the two environments. Any optional generative AI must stay inside Amazon Bedrock, including its Mantle inference endpoint; the core OTDR, outage, and field-plan results cannot depend on an LLM.

## Decision

Maintain one Next.js/FastAPI codebase and the same OCI images for both deployment surfaces:

- **Demo:** Docker Compose runs Next.js, FastAPI, and a seeded PostGIS database with one command.
- **Production:** Helm deploys the images to EKS behind an AWS Application Load Balancer. PostgreSQL/PostGIS is supplied by RDS, credentials come from AWS Secrets Manager through External Secrets, and workload identity uses EKS IRSA.
- **AI:** A deterministic guided parser is the default. `AI_PROVIDER=bedrock_mantle` may extract bounded intake fields and add a non-authoritative narrative summary through `https://bedrock-mantle.us-east-1.api.aws/v1`; response storage is disabled. Provider data and deterministic results remain authoritative. No OpenAI-hosted endpoint or API key is accepted by the adapter.
- **Network data:** `NetworkDataProvider` isolates the PostGIS demo implementation. The VETRO adapter remains an explicit stub until an approved endpoint and schema are available.

## Options considered

| Option | Complexity | Demo fidelity | Production fit | Assessment |
|---|---:|---:|---:|---|
| Separate demo and production applications | High | High | High | Rejected; behavior and fixes would drift. |
| Docker Compose in both environments | Low | High | Low | Rejected; insufficient orchestration, identity, and availability controls for production. |
| One codebase, Compose + EKS surfaces | Medium | High | High | Selected; portable behavior with environment-specific operations. |

## Consequences

- Domain algorithms, tests, migrations, and container images stay common.
- Production requires an existing EKS cluster, AWS Load Balancer Controller, RDS/PostGIS, ECR, and optionally External Secrets Operator.
- Database migrations run as an idempotent Helm install/upgrade hook; demo seed data is disabled in production values.
- Mantle API keys must be AWS-issued and stored in Secrets Manager. If AI is disabled, guided intake and the full structured plan still work without pretending an LLM is active.
- A real VETRO integration is a later adapter implementation, not a rewrite.

## Action items

1. Provision production AWS prerequisites and inject their identifiers into Helm values.
2. Obtain and document an approved VETRO read schema before implementing the stub.
3. Add authentication/authorization and audit retention before exposing production data.
