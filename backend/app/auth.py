from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from urllib.parse import urlparse

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    subject: str
    tenant_id: str
    display_name: str
    username: str | None
    scopes: tuple[str, ...]
    roles: tuple[str, ...]


class EntraTokenValidator:
    """Validate tenant-specific Entra v2 access tokens for this API."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._keys: dict[str, dict[str, Any]] = {}
        self._expires_at = 0.0
        self._lock = asyncio.Lock()

    async def validate(self, token: str) -> Principal:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise self._unauthorized() from exc

        if header.get("alg") != "RS256" or not isinstance(header.get("kid"), str):
            raise self._unauthorized()

        key = await self._get_key(header["kid"])
        try:
            claims = jwt.decode(
                token,
                jwt.PyJWK.from_dict(key, algorithm="RS256").key,
                algorithms=["RS256"],
                audience=self.settings.entra_token_audience,
                issuer=self.settings.entra_issuer,
                leeway=60,
                options={"require": ["aud", "exp", "iat", "iss", "nbf", "sub", "tid"]},
            )
        except jwt.PyJWTError as exc:
            raise self._unauthorized() from exc

        if claims.get("tid") != self.settings.entra_tenant_id:
            raise self._unauthorized()

        authorized_client = claims.get("azp") or claims.get("appid")
        if authorized_client != self.settings.entra_client_id:
            raise self._forbidden("The calling application is not authorized for Photon-Ops.")

        scopes = tuple(str(claims.get("scp", "")).split())
        roles = tuple(str(role) for role in claims.get("roles", []) if isinstance(role, str))
        required = self.settings.entra_required_scope
        if required not in scopes and required not in roles:
            raise self._forbidden("The required Photon-Ops API permission is missing.")

        return Principal(
            subject=str(claims["sub"]),
            tenant_id=str(claims["tid"]),
            display_name=str(claims.get("name") or claims.get("preferred_username") or "Operator"),
            username=(
                str(claims["preferred_username"])
                if claims.get("preferred_username")
                else None
            ),
            scopes=scopes,
            roles=roles,
        )

    async def _get_key(self, key_id: str) -> dict[str, Any]:
        if time.monotonic() >= self._expires_at or key_id not in self._keys:
            await self._refresh_keys()
        key = self._keys.get(key_id)
        if not key:
            raise self._unauthorized()
        return key

    async def _refresh_keys(self) -> None:
        async with self._lock:
            if time.monotonic() < self._expires_at and self._keys:
                return
            try:
                async with httpx.AsyncClient(timeout=5, follow_redirects=False) as client:
                    metadata_response = await client.get(self.settings.entra_metadata_url)
                    metadata_response.raise_for_status()
                    metadata = metadata_response.json()
                    jwks_uri = str(metadata["jwks_uri"])
                    parsed = urlparse(jwks_uri)
                    if parsed.scheme != "https" or parsed.hostname != "login.microsoftonline.com":
                        raise ValueError("Unexpected Entra JWKS endpoint")
                    keys_response = await client.get(jwks_uri)
                    keys_response.raise_for_status()
                    keys = keys_response.json().get("keys", [])
            except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Identity provider metadata is temporarily unavailable.",
                ) from exc

            self._keys = {
                str(key["kid"]): key
                for key in keys
                if isinstance(key, dict)
                and key.get("kid")
                and key.get("kty") == "RSA"
                and key.get("use") in (None, "sig")
            }
            if not self._keys:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Identity provider signing keys are unavailable.",
                )
            self._expires_at = time.monotonic() + self.settings.oidc_cache_ttl_seconds

    @staticmethod
    def _unauthorized() -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid Microsoft Entra ID access token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    @staticmethod
    def _forbidden(detail: str) -> HTTPException:
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


@lru_cache
def get_token_validator() -> EntraTokenValidator:
    return EntraTokenValidator(get_settings())


async def require_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> Principal:
    settings = get_settings()
    if settings.auth_mode == "disabled":
        return Principal(
            subject="demo-operator",
            tenant_id="local-demo",
            display_name="Docker demo operator",
            username=None,
            scopes=("demo",),
            roles=("operator",),
        )
    if not credentials or credentials.scheme.lower() != "bearer":
        raise EntraTokenValidator._unauthorized()
    return await get_token_validator().validate(credentials.credentials)
