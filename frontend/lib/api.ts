import type {
  CircuitPath,
  NavigatorCapabilities,
  NavigatorIntake,
  NavigatorMessage,
  Correlation,
  DemoOverview,
  FieldPlan,
  OutageImpact,
  SearchResult,
} from "@/types/network";

type AccessTokenProvider = () => Promise<string | null>;

let accessTokenProvider: AccessTokenProvider | null = null;

export function setAccessTokenProvider(provider: AccessTokenProvider | null): void {
  accessTokenProvider = provider;
}

export function apiBase(): string {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
  if (typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname)) {
    return "http://localhost:8000";
  }
  return "";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = accessTokenProvider ? await accessTokenProvider() : null;
  const response = await fetch(`${apiBase()}${path}`, {
    ...init,
    cache: "no-store",
    credentials: "omit",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Unknown API error" }));
    throw new Error(body.detail ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  authConfig: () => request<AuthConfig>("/api/auth/config"),
  currentIdentity: () => request<Identity>("/api/auth/me"),
  overview: () => request<DemoOverview>("/api/demo/overview"),
  navigatorCapabilities: () => request<NavigatorCapabilities>("/api/navigator/capabilities"),
  navigatorIntake: (messages: NavigatorMessage[]) =>
    request<NavigatorIntake>("/api/navigator/intake", {
      method: "POST",
      body: JSON.stringify({ messages }),
    }),
  search: (query: string) => request<SearchResult[]>(`/api/assets/search?q=${encodeURIComponent(query)}`),
  circuitPath: (circuitId: string) => request<CircuitPath>(`/api/circuits/${circuitId}/path`),
  servicePath: (serviceLocationId: string) =>
    request<CircuitPath>(`/api/service-locations/${serviceLocationId}/path`),
  correlate: (payload: {
    circuit_id: string;
    launch_asset_id: string;
    fault_distance_ft: number;
    tolerance_ft: number;
  }) => request<Correlation>("/api/analysis/otdr-correlate", { method: "POST", body: JSON.stringify(payload) }),
  outageImpact: (assetId: string) => request<OutageImpact>(`/api/analysis/outage-impact/${assetId}`),
  fieldPlan: (payload: {
    circuit_id: string;
    launch_asset_id: string;
    fault_distance_ft: number;
    tolerance_ft: number;
    impact_asset_id?: string;
  }) => request<FieldPlan>("/api/reports/field-action-plan", { method: "POST", body: JSON.stringify(payload) }),
};

export type AuthConfig =
  | { mode: "disabled" }
  | {
      mode: "entra";
      tenant_id: string;
      client_id: string;
      authority: string;
      api_scope: string;
    };

export type Identity = {
  subject: string;
  tenant_id: string;
  display_name: string;
  username: string | null;
  scopes: string[];
  roles: string[];
};
