# ADR 0002: Integrate Photon Bench and protect production with Entra ID

- Status: Accepted
- Date: 2026-07-20

## Context

Fiber operations decisions need both plant context and optical feasibility. A standalone calculator requires operators to re-enter circuit distance and event assumptions, while a map-only console cannot answer whether a selected route fits the equipment power window. Production access also requires organization-owned identity rather than a shared local credential.

## Decision

Rename the product Photon-Ops Navigator and make Photon Bench a first-class workspace in the same Next.js application. The operations and optical workspaces share the selected circuit and ordered route returned by FastAPI. Photon Bench uses the prior Fiber Ledger planning allowances for OS2 and OM4 links, exposes FOA typical and ANSI/TIA maximum profiles, and clearly labels outputs as planning guidance rather than acceptance-test results.

Use Microsoft Entra ID as the production identity provider. The browser uses MSAL authorization code flow with PKCE and requests the API’s `access_as_user` delegated scope. FastAPI independently validates the access token’s signature, issuer, tenant, audience, calling client, lifetime, and scope. EKS fails closed if Entra mode or identifiers are missing. Docker remains explicitly anonymous by default for a self-contained local demo.

## Consequences

- Circuit distance moves into the optical model without manual transcription.
- The full operational workflow remains in one product and one deployment artifact.
- The calculator is useful for planning but does not claim OLTS certification or replace bidirectional OTDR interpretation.
- Production requires two single-tenant Entra app registrations and administrator-approved delegated permission.
- A future authorization ADR must map Entra roles to read-only, operator, and administrator capabilities before the API gains write operations.
