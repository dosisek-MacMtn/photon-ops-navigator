# Microsoft Entra ID setup

Photon-Ops Navigator uses a browser public client and a separately registered protected API. It is single-tenant by design: the API accepts only tokens issued by the configured tenant, intended for the configured API, requested by the configured SPA, and carrying the configured delegated scope.

## 1. Register the API

1. In Microsoft Entra admin center, create an app registration named `Photon-Ops API` for accounts in this organizational directory only.
2. Record its application (client) ID as `ENTRA_API_CLIENT_ID` and the directory tenant ID as `ENTRA_TENANT_ID`.
3. Under **Expose an API**, accept `api://<API_CLIENT_ID>` as the Application ID URI.
4. Add a delegated scope named `access_as_user`. Require administrator consent if that matches organizational policy.
5. Do not create a client secret for this API integration. Access tokens are verified with Entra’s published signing keys.

## 2. Register the SPA

1. Create an app registration named `Photon-Ops SPA`, again single-tenant.
2. Record its application ID as `ENTRA_CLIENT_ID`.
3. Add **Single-page application** redirect URIs:
   - `http://localhost:3000`
   - the exact production origin, for example `https://photonops.example.com`
4. Add delegated API permission `Photon-Ops API / access_as_user` and grant the required consent.
5. Leave implicit grant disabled. MSAL uses the authorization code flow with PKCE.

## 3. Configure Docker

Copy `.env.example` to `.env`, change `AUTH_MODE` to `entra`, and fill the three GUIDs. `ENTRA_AUDIENCE` can remain blank; it defaults to `ENTRA_API_CLIENT_ID`.

```bash
docker compose up --build
```

The browser is redirected to the tenant-specific Microsoft sign-in endpoint. Tokens are stored in session storage and attached only to Photon-Ops API calls.

## 4. Configure EKS

Supply the identifiers as Helm values. Client and tenant IDs are identifiers, not credentials, so the chart keeps them in its ConfigMap.

```bash
helm upgrade --install photonops deploy/helm/photon-ops-navigator \
  --namespace photonops --create-namespace \
  --set auth.tenantId=TENANT_GUID \
  --set auth.clientId=SPA_CLIENT_GUID \
  --set auth.apiClientId=API_CLIENT_GUID \
  --set ingress.host=photonops.example.com
```

The API refuses to start in `production` if authentication is disabled or required Entra identifiers are absent. The local demo may remain anonymous because `ENVIRONMENT=demo` and `AUTH_MODE=disabled` are explicit.

## Validated claims

For every protected API request, FastAPI validates:

- RSA signature from the tenant-specific Entra discovery document
- `alg=RS256` and a known `kid`
- exact v2 issuer and tenant ID
- API audience
- authorized SPA client (`azp`/`appid`)
- `iat`, `nbf`, and `exp`
- delegated `access_as_user` scope or equivalent app role

Health probes and `/api/auth/config` are intentionally unauthenticated. Operational data, analysis, reports, and `/api/auth/me` require a valid access token whenever Entra mode is enabled.
