from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse
from uuid import UUID

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Photon-Ops Navigator"
    environment: str = "development"
    database_url: str = "postgresql+asyncpg://photonops:photonops@db:5432/photonops"
    network_provider: Literal["demo", "vetro"] = "demo"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    auth_mode: Literal["disabled", "entra"] = "disabled"
    allow_insecure_production_auth: bool = False
    entra_tenant_id: str | None = None
    entra_client_id: str | None = None
    entra_api_client_id: str | None = None
    entra_audience: str | None = None
    entra_required_scope: str = "access_as_user"
    oidc_cache_ttl_seconds: int = Field(default=3600, ge=300, le=86400)

    ai_provider: Literal["deterministic", "bedrock_mantle"] = "deterministic"
    aws_region: str = "us-east-1"
    bedrock_mantle_base_url: str | None = None
    bedrock_api_key: str | None = None
    bedrock_model: str = "openai.gpt-oss-120b"

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, origins: list[str]) -> list[str]:
        if not origins:
            raise ValueError("CORS_ORIGINS must contain at least one application origin")
        for origin in origins:
            parsed = urlparse(origin)
            if origin == "*" or parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("CORS_ORIGINS must contain explicit HTTP(S) origins")
            if parsed.path not in {"", "/"} or parsed.params or parsed.query or parsed.fragment:
                raise ValueError("CORS_ORIGINS entries cannot include paths, queries, or fragments")
        return origins

    @model_validator(mode="after")
    def validate_security_configuration(self):
        if (
            self.environment == "production"
            and self.auth_mode == "disabled"
            and not self.allow_insecure_production_auth
        ):
            raise ValueError("AUTH_MODE=entra is required in production")
        if self.auth_mode == "entra":
            required_ids = {
                "ENTRA_TENANT_ID": self.entra_tenant_id,
                "ENTRA_CLIENT_ID": self.entra_client_id,
                "ENTRA_API_CLIENT_ID": self.entra_api_client_id,
            }
            for name, value in required_ids.items():
                if not value:
                    raise ValueError(f"{name} is required when AUTH_MODE=entra")
                try:
                    UUID(value)
                except ValueError as exc:
                    raise ValueError(f"{name} must be a GUID") from exc
        return self

    @property
    def mantle_base_url(self) -> str:
        return self.bedrock_mantle_base_url or (
            f"https://bedrock-mantle.{self.aws_region}.api.aws/v1"
        )

    @property
    def entra_authority(self) -> str:
        if not self.entra_tenant_id:
            raise ValueError("ENTRA_TENANT_ID is required when AUTH_MODE=entra")
        return f"https://login.microsoftonline.com/{self.entra_tenant_id}"

    @property
    def entra_issuer(self) -> str:
        return f"{self.entra_authority}/v2.0"

    @property
    def entra_metadata_url(self) -> str:
        return f"{self.entra_issuer}/.well-known/openid-configuration"

    @property
    def entra_token_audience(self) -> str:
        audience = self.entra_audience or self.entra_api_client_id
        if not audience:
            raise ValueError("ENTRA_API_CLIENT_ID or ENTRA_AUDIENCE is required")
        return audience

    @property
    def entra_api_scope(self) -> str:
        if not self.entra_api_client_id:
            raise ValueError("ENTRA_API_CLIENT_ID is required when AUTH_MODE=entra")
        return f"api://{self.entra_api_client_id}/{self.entra_required_scope}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
