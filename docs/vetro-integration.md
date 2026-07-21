# VETRO FiberMap integration gate

Photon-Ops Navigator is ready to call VETRO through the `NetworkDataProvider` boundary, but the repository does not fabricate VETRO endpoints or response schemas.

## Required production inputs

Before implementing and enabling `NETWORK_PROVIDER=vetro`, obtain these items from the organization’s VETRO tenant or VETRO support:

1. Region- and tenant-specific API base URL.
2. Current customer API documentation for asset search, circuit/path retrieval, nearby spatial lookup, outage/topology relationships, splice connectivity, and any required pagination.
3. A read-only authentication mechanism and secret-rotation process.
4. Approved mappings from VETRO object types and identifiers into `AssetResponse`, `SearchResult`, `CircuitPathResponse`, `OutageImpactResponse`, and the splice-connectivity graph described below.
5. Rate limits, timeout guidance, audit requirements, and a non-production test tenant or fixture export.

## Splicing data contract

Yes: the production adapter should retrieve VETRO splice connectivity as part of a circuit trace when the tenant's approved API profile exposes it. Photon-Ops must preserve the connectivity graph instead of reducing it to prose. The approved mapping should include, where available:

- Fiber cables, tube/buffer identifiers, fiber counts, and individual strand number, color, and status.
- Splice enclosures, closures, cases, trays/cassettes, patch panels, adapters, and equipment ports.
- Inbound and outbound cable/strand endpoints for every A-to-B splice or connector relationship.
- Circuit membership and ordered traversal so an operator can trace a strand through each closure and port.
- Premise/service-address relationships and the serving LCP, splitter, and splitter port used to build an address-first residential path.
- Splice type, planned/as-built state, measured or engineered loss, timestamp, source record, and notes when the tenant permits them.

The first implementation should expose read-only address/service-location-, circuit-, and asset-scoped retrieval. A safe normalized response has `nodes` for premises, LCPs, cables, strands, closures, trays, and ports; `connections` for splitter, splice, and patch relationships; and provider audit identifiers on every record. Missing optional fields must stay explicitly unknown rather than being inferred. The UI can then trace an address from its serving LCP splitter port, place closure events on the satellite route, open tray/strand detail, and feed verified splitter and splice loss into Photon Bench.

## Security requirements

- Store credentials in AWS Secrets Manager and inject them into EKS through the approved secrets mechanism.
- Grant only read operations required by the provider contract.
- Do not send bearer tokens to the browser or log them in API errors.
- Apply explicit connection/read timeouts, bounded retries with jitter, pagination limits, and circuit breakers.
- Validate every upstream response before it reaches analysis code.
- Preserve tenant isolation and provider audit identifiers in centralized logs.
- Complete contract tests against the approved sandbox before production enablement.

## Current behavior

- Docker uses the seeded PostGIS implementation and labels it `Demo PostGIS`.
- The Navigator intake calls the provider boundary before marking a circuit verified.
- The VETRO production gate now explicitly includes splice closures, trays, strands, ports, and ordered splice relationships.
- Selecting VETRO while the contract stub is present returns an honest `provider_unavailable` state.
- The UI labels VETRO as `Profile required`; it does not claim a live integration.

VETRO’s public documentation landing page states that API documentation is available to customers after login. The tenant documentation therefore remains a production prerequisite: <https://docs.fibermap.vetro.io/>.
