"use client";

import {
  AccountInfo,
  InteractionRequiredAuthError,
  PublicClientApplication,
} from "@azure/msal-browser";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { api, type AuthConfig, setAccessTokenProvider } from "@/lib/api";

type AuthState = {
  mode: "disabled" | "entra";
  ready: boolean;
  account: AccountInfo | null;
  displayName: string;
  username: string | null;
  login: () => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [config, setConfig] = useState<AuthConfig | null>(null);
  const [client, setClient] = useState<PublicClientApplication | null>(null);
  const [account, setAccount] = useState<AccountInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    api.authConfig()
      .then(async (nextConfig) => {
        if (!active) return;
        setConfig(nextConfig);
        if (nextConfig.mode === "disabled") {
          setAccessTokenProvider(async () => null);
          return;
        }

        const instance = new PublicClientApplication({
          auth: {
            clientId: nextConfig.client_id,
            authority: nextConfig.authority,
            redirectUri: window.location.origin,
            postLogoutRedirectUri: window.location.origin,
          },
          cache: { cacheLocation: "sessionStorage" },
          system: { allowPlatformBroker: false },
        });
        await instance.initialize();
        const redirect = await instance.handleRedirectPromise();
        const nextAccount = redirect?.account ?? instance.getAllAccounts()[0] ?? null;
        if (nextAccount) instance.setActiveAccount(nextAccount);
        if (!active) return;
        setClient(instance);
        setAccount(nextAccount);
        setAccessTokenProvider(async () => {
          const activeAccount = instance.getActiveAccount() ?? instance.getAllAccounts()[0];
          if (!activeAccount) return null;
          try {
            const result = await instance.acquireTokenSilent({
              account: activeAccount,
              scopes: [nextConfig.api_scope],
            });
            return result.accessToken;
          } catch (tokenError) {
            if (tokenError instanceof InteractionRequiredAuthError) {
              await instance.acquireTokenRedirect({
                account: activeAccount,
                scopes: [nextConfig.api_scope],
              });
            }
            throw tokenError;
          }
        });
      })
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof Error ? cause.message : "Authentication could not start.");
      });
    return () => {
      active = false;
      setAccessTokenProvider(null);
    };
  }, []);

  const login = useCallback(async () => {
    if (!client || config?.mode !== "entra") return;
    await client.loginRedirect({ scopes: [config.api_scope], prompt: "select_account" });
  }, [client, config]);

  const logout = useCallback(async () => {
    if (!client || !account) return;
    await client.logoutRedirect({ account });
  }, [account, client]);

  const value = useMemo<AuthState>(
    () => ({
      mode: config?.mode ?? "disabled",
      ready: Boolean(config),
      account,
      displayName:
        config?.mode === "disabled"
          ? "Docker demo operator"
          : account?.name ?? account?.username ?? "Operator",
      username: config?.mode === "disabled" ? null : account?.username ?? null,
      login,
      logout,
    }),
    [account, config, login, logout],
  );

  if (error) {
    return (
      <main className="auth-screen">
        <div className="auth-card">
          <span className="auth-status alarm">Identity unavailable</span>
          <h1>Photon-Ops Navigator</h1>
          <p>{error}</p>
          <button onClick={() => window.location.reload()}>Retry connection</button>
        </div>
      </main>
    );
  }

  if (!config || (config.mode === "entra" && !client)) {
    return (
      <main className="auth-screen">
        <div className="auth-card">
          <span className="auth-status">Secure workspace</span>
          <h1>Photon-Ops Navigator</h1>
          <p>Connecting to the identity service…</p>
          <span className="auth-loader" aria-label="Loading" />
        </div>
      </main>
    );
  }

  if (config.mode === "entra" && !account) {
    return (
      <main className="auth-screen">
        <div className="auth-card">
          <span className="auth-status">Microsoft Entra ID</span>
          <h1>Operate the route.<br />Understand the light.</h1>
          <p>Sign in with your organization account to open the network assurance workspace.</p>
          <button onClick={login}>Sign in with Microsoft</button>
          <small>Single-tenant access · Authorization code with PKCE</small>
        </div>
      </main>
    );
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
