from __future__ import annotations

import math
from typing import Any

from app.adapters.base import NetworkDataProvider, ProviderNotFoundError
from app.demo_data import build_demo_network
from app.services.topology import calculate_graph_impact


def _service_lineage(location: dict[str, Any], premise: dict[str, Any]) -> dict[str, Any]:
    metadata = premise["metadata"]
    return {
        "account_type": location["account_type"],
        "premise_asset_id": premise["id"],
        "lcp_asset_id": metadata["serving_lcp_id"],
        "lcp_name": metadata["serving_lcp_name"],
        "lcp_code": metadata["serving_lcp_code"],
        "splitter_id": metadata["splitter_id"],
        "splitter_ratio": metadata["splitter_ratio"],
        "splitter_port": metadata["splitter_port"],
    }


class InMemoryNetworkDataProvider(NetworkDataProvider):
    """Deterministic provider for tests; production demos use PostGIS."""

    def __init__(self, data: dict[str, Any] | None = None):
        self.data = data or build_demo_network()
        self.assets = {item["id"]: item for item in self.data["assets"]}
        self.cables = {item["id"]: item for item in self.data["cables"]}
        self.locations = {item["id"]: item for item in self.data["service_locations"]}
        self.circuits = {item["id"]: item for item in self.data["circuits"]}

    async def search_assets(self, query: str):
        normalized = query.strip().lower()
        results: list[dict[str, str]] = []
        for location in self.locations.values():
            if normalized in location["address"].lower() or normalized in location["id"]:
                related_circuit = next(
                    (
                        circuit["id"]
                        for circuit in self.circuits.values()
                        if circuit["service_location_id"] == location["id"]
                    ),
                    None,
                )
                if related_circuit:
                    premise = self.assets[location["asset_id"]]
                    metadata = premise["metadata"]
                    circuit = self.circuits[related_circuit]
                    results.append(
                        {
                            "id": location["id"],
                            "result_type": "service_location",
                            "name": location["address"],
                            "subtitle": (
                                f"{location['account_type'].title()} · "
                                f"{metadata['serving_lcp_code']} / "
                                f"{metadata['splitter_id']} / "
                                f"Port {metadata['splitter_port']:02d} · {circuit['name']}"
                            ),
                            "related_circuit_id": related_circuit,
                        }
                    )
        for circuit in self.circuits.values():
            location = self.locations[circuit["service_location_id"]]
            if normalized in circuit["id"].lower() or normalized in circuit["name"].lower():
                metadata = self.assets[location["asset_id"]]["metadata"]
                results.append(
                    {
                        "id": circuit["id"],
                        "result_type": "circuit",
                        "name": circuit["name"],
                        "subtitle": (
                            f"{location['address']} · {metadata['serving_lcp_code']} / "
                            f"{metadata['splitter_id']} / "
                            f"Port {metadata['splitter_port']:02d}"
                        ),
                        "related_circuit_id": circuit["id"],
                    }
                )
        for asset in self.assets.values():
            if asset["asset_type"] == "service_location":
                continue
            if normalized in asset["id"].lower() or normalized in asset["name"].lower():
                results.append(
                    {
                        "id": asset["id"],
                        "result_type": "asset",
                        "name": asset["name"],
                        "subtitle": asset["asset_type"].replace("_", " ").title(),
                    }
                )
        return results[:25]

    async def get_asset(self, asset_id: str):
        if asset_id not in self.assets:
            raise ProviderNotFoundError(f"Asset {asset_id} was not found")
        return self.assets[asset_id]

    async def get_circuit_path(self, circuit_id: str):
        if circuit_id not in self.circuits:
            raise ProviderNotFoundError(f"Circuit {circuit_id} was not found")
        circuit = self.circuits[circuit_id]
        location = self.locations[circuit["service_location_id"]]
        premise = self.assets[location["asset_id"]]
        cumulative = 0.0
        segments = []
        raw_segments = sorted(
            (item for item in self.data["path_segments"] if item["circuit_id"] == circuit_id),
            key=lambda item: item["sequence"],
        )
        for raw in raw_segments:
            cable = self.cables[raw["cable_id"]]
            segment = {
                **raw,
                "cable_name": cable["name"],
                "cable_type": cable["cable_type"],
                "start_asset_name": self.assets[raw["start_asset_id"]]["name"],
                "end_asset_name": self.assets[raw["end_asset_id"]]["name"],
                "cumulative_start_ft": cumulative,
                "cumulative_end_ft": cumulative + raw["length_ft"],
                "coordinates": cable["coordinates"],
            }
            cumulative += raw["length_ft"]
            segments.append(segment)
        service_lineage = _service_lineage(location, premise)
        service_leg_segments = next(
            (
                segments[index:]
                for index, segment in enumerate(segments)
                if segment["start_asset_id"] == service_lineage["lcp_asset_id"]
            ),
            segments,
        )
        return {
            "circuit_id": circuit_id,
            "circuit_name": circuit["name"],
            "service_location_id": location["id"],
            "service_address": location["address"],
            "service_lineage": service_lineage,
            "total_length_ft": cumulative,
            "service_leg_start_sequence": service_leg_segments[0]["sequence"],
            "service_leg_length_ft": sum(
                segment["length_ft"] for segment in service_leg_segments
            ),
            "service_leg_segments": service_leg_segments,
            "segments": segments,
        }

    async def get_service_path(self, service_location_id: str):
        circuit_id = next(
            (
                circuit["id"]
                for circuit in self.circuits.values()
                if circuit["service_location_id"] == service_location_id
            ),
            None,
        )
        if not circuit_id:
            raise ProviderNotFoundError(
                f"Active service for address record {service_location_id} was not found"
            )
        return await self.get_circuit_path(circuit_id)

    async def get_assets_nearby(self, latitude: float, longitude: float, radius_ft: float):
        nearby = []
        for asset in self.assets.values():
            lat_scale = 364000
            lon_scale = 364000 * math.cos(math.radians(latitude))
            distance = math.hypot(
                (asset["latitude"] - latitude) * lat_scale,
                (asset["longitude"] - longitude) * lon_scale,
            )
            if distance <= radius_ft:
                nearby.append({**asset, "distance_ft": round(distance, 1)})
        return sorted(nearby, key=lambda item: item["distance_ft"])

    async def calculate_outage_impact(self, asset_id: str):
        return calculate_graph_impact(
            asset_id,
            self.data["cables"],
            self.data["circuits"],
            self.data["path_segments"],
            self.data["service_locations"],
            {item["id"]: item["asset_type"] for item in self.data["assets"]},
        )

    async def get_overview(self):
        summaries = []
        for circuit in self.data["circuits"]:
            location = self.locations[circuit["service_location_id"]]
            summaries.append(
                {
                    "id": circuit["id"],
                    "name": circuit["name"],
                    "service_address": location["address"],
                    "service_location_id": location["id"],
                    "service_lineage": _service_lineage(
                        location,
                        self.assets[location["asset_id"]],
                    ),
                    "status": circuit["status"],
                }
            )
        return {
            "assets": self.data["assets"],
            "cables": self.data["cables"],
            "circuits": summaries,
            "incidents": self.data["incidents"],
        }
