import pytest
from fastapi.testclient import TestClient

from app.adapters.memory import InMemoryNetworkDataProvider
from app.dependencies import get_provider
from app.main import app


@pytest.fixture
def provider():
    return InMemoryNetworkDataProvider()


@pytest.fixture
def client(provider):
    async def override_provider():
        return provider

    app.dependency_overrides[get_provider] = override_provider
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
