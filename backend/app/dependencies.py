from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import NetworkDataProvider
from app.adapters.demo import DemoNetworkDataProvider
from app.adapters.vetro import VetroNetworkDataProvider
from app.config import get_settings
from app.database import get_session


async def get_provider(
    session: AsyncSession = Depends(get_session),
) -> NetworkDataProvider:
    provider_name = get_settings().network_provider
    if provider_name == "demo":
        return DemoNetworkDataProvider(session)
    if provider_name == "vetro":
        return VetroNetworkDataProvider()
    raise RuntimeError(f"Unknown NETWORK_PROVIDER: {provider_name}")
