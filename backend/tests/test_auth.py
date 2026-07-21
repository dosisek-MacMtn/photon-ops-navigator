import time
from uuid import UUID

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from app.auth import EntraTokenValidator
from app.config import Settings

TENANT_ID = "11111111-1111-4111-8111-111111111111"
CLIENT_ID = "22222222-2222-4222-8222-222222222222"
API_CLIENT_ID = "33333333-3333-4333-8333-333333333333"


def test_demo_auth_config_and_identity(client):
    config = client.get("/api/auth/config")
    assert config.status_code == 200
    assert config.json() == {"mode": "disabled"}

    identity = client.get("/api/auth/me")
    assert identity.status_code == 200
    assert identity.json()["display_name"] == "Docker demo operator"
    assert identity.headers["x-content-type-options"] == "nosniff"
    assert identity.headers["cache-control"] == "no-store"


@pytest.mark.asyncio
async def test_entra_validator_checks_signature_tenant_audience_client_and_scope():
    settings = Settings(
        _env_file=None,
        environment="test",
        auth_mode="entra",
        entra_tenant_id=TENANT_ID,
        entra_client_id=CLIENT_ID,
        entra_api_client_id=API_CLIENT_ID,
    )
    validator = EntraTokenValidator(settings)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    public_jwk.update({"kid": "test-key", "use": "sig", "alg": "RS256"})
    validator._keys = {"test-key": public_jwk}
    validator._expires_at = time.monotonic() + 600

    now = int(time.time())
    claims = {
        "aud": API_CLIENT_ID,
        "iss": f"https://login.microsoftonline.com/{TENANT_ID}/v2.0",
        "iat": now,
        "nbf": now,
        "exp": now + 600,
        "sub": "operator-subject",
        "tid": TENANT_ID,
        "azp": CLIENT_ID,
        "scp": "access_as_user",
        "name": "Network Operator",
        "preferred_username": "operator@example.com",
    }
    token = jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "test-key"})

    principal = await validator.validate(token)
    assert principal.display_name == "Network Operator"
    assert principal.tenant_id == TENANT_ID
    assert "access_as_user" in principal.scopes

    wrong_audience = jwt.encode(
        {**claims, "aud": str(UUID(int=4))},
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )
    with pytest.raises(HTTPException) as error:
        await validator.validate(wrong_audience)
    assert error.value.status_code == 401


def test_production_fails_closed_without_entra():
    with pytest.raises(ValueError, match="AUTH_MODE=entra"):
        Settings(_env_file=None, environment="production", auth_mode="disabled")
