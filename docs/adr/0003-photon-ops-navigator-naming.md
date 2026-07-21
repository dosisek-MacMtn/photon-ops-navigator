# ADR 0003: Use Photon-Ops Navigator as the product name

- Status: Accepted
- Date: 2026-07-21

## Context

The previous assistant-oriented suffix overlaps with Microsoft’s broad AI product naming and could imply an affiliation that does not exist. The product needs a distinct name that reflects guided fiber investigation, route tracing, address and circuit resolution, satellite context, VETRO integration, and handoff into Photon Bench.

## Decision

Use **Photon-Ops Navigator** as the product name. Treat **Photon-Ops** as the platform family, **Navigator** as the guided operational investigation experience, and **Photon Bench** as the integrated optical engineering workspace.

Rename the public API intake surface to `/api/navigator`, use `photon-ops-navigator` for Docker, Helm, package, and repository identifiers, and apply the same name to executive collateral and deployment documentation.

## Consequences

- The product has a distinct identity that does not imply Microsoft affiliation.
- Operators get a consistent “Navigator” vocabulary from intake through verified investigation.
- The API route change is intentionally breaking for pre-release clients; the bundled frontend is updated in the same release.
- Photon Bench retains its established name and remains a first-class module inside Photon-Ops Navigator.
