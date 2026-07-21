from abc import ABC, abstractmethod


class NetworkDataProvider(ABC):
    @abstractmethod
    async def search_assets(self, query: str): ...

    @abstractmethod
    async def get_asset(self, asset_id: str): ...

    @abstractmethod
    async def get_circuit_path(self, circuit_id: str): ...

    @abstractmethod
    async def get_service_path(self, service_location_id: str): ...

    @abstractmethod
    async def get_assets_nearby(
        self,
        latitude: float,
        longitude: float,
        radius_ft: float,
    ): ...

    @abstractmethod
    async def calculate_outage_impact(self, asset_id: str): ...

    @abstractmethod
    async def get_overview(self): ...


class ProviderNotFoundError(LookupError):
    pass
