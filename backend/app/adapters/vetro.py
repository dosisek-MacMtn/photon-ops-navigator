from app.adapters.base import NetworkDataProvider


class VetroNetworkDataProvider(NetworkDataProvider):
    """Documented contract stub; no VETRO endpoints or schemas are assumed."""

    def _not_configured(self):
        raise NotImplementedError(
            "The VETRO adapter is a contract stub. Configure an approved VETRO "
            "API/export schema before enabling it."
        )

    async def search_assets(self, query: str):
        self._not_configured()

    async def get_asset(self, asset_id: str):
        self._not_configured()

    async def get_circuit_path(self, circuit_id: str):
        self._not_configured()

    async def get_service_path(self, service_location_id: str):
        self._not_configured()

    async def get_assets_nearby(self, latitude: float, longitude: float, radius_ft: float):
        self._not_configured()

    async def calculate_outage_impact(self, asset_id: str):
        self._not_configured()

    async def get_overview(self):
        self._not_configured()
