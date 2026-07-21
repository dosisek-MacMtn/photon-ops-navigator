from __future__ import annotations

from typing import Any

from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import NetworkDataProvider, ProviderNotFoundError
from app.demo_data import INCIDENTS
from app.models import Asset, Cable, Circuit, CircuitPathSegment, ServiceLocation
from app.services.topology import calculate_graph_impact


def _asset_dict(asset: Asset) -> dict[str, Any]:
    return {
        "id": asset.id,
        "name": asset.name,
        "asset_type": asset.asset_type,
        "status": asset.status,
        "latitude": asset.latitude,
        "longitude": asset.longitude,
        "metadata": asset.metadata_json or {},
    }


def _cable_dict(cable: Cable) -> dict[str, Any]:
    return {
        "id": cable.id,
        "name": cable.name,
        "cable_type": cable.cable_type,
        "start_asset_id": cable.start_asset_id,
        "end_asset_id": cable.end_asset_id,
        "length_ft": cable.length_ft,
        "fiber_count": cable.fiber_count,
        "status": cable.status,
        "coordinates": cable.coordinates,
    }


def _service_lineage(location: ServiceLocation, premise: Asset) -> dict[str, Any]:
    metadata = premise.metadata_json or {}
    return {
        "account_type": location.account_type,
        "premise_asset_id": premise.id,
        "lcp_asset_id": str(metadata["serving_lcp_id"]),
        "lcp_name": str(metadata["serving_lcp_name"]),
        "lcp_code": str(metadata["serving_lcp_code"]),
        "splitter_id": str(metadata["splitter_id"]),
        "splitter_ratio": str(metadata["splitter_ratio"]),
        "splitter_port": int(metadata["splitter_port"]),
    }


class DemoNetworkDataProvider(NetworkDataProvider):
    """PostgreSQL/PostGIS-backed provider for the deterministic demo network."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def search_assets(self, query: str):
        normalized = query.strip()
        pattern = f"%{normalized}%"
        results: list[dict[str, str]] = []

        location_rows = (
            await self.session.execute(
                select(ServiceLocation, Circuit, Asset)
                .join(Circuit, Circuit.service_location_id == ServiceLocation.id)
                .join(Asset, ServiceLocation.asset_id == Asset.id)
                .where(
                    or_(
                        ServiceLocation.id.ilike(pattern),
                        ServiceLocation.address.ilike(pattern),
                    )
                )
                .limit(10)
            )
        ).all()
        results.extend(
            {
                "id": location.id,
                "result_type": "service_location",
                "name": location.address,
                "subtitle": (
                    f"{location.account_type.title()} · "
                    f"{premise.metadata_json['serving_lcp_code']} / "
                    f"{premise.metadata_json['splitter_id']} / "
                    f"Port {int(premise.metadata_json['splitter_port']):02d} · {circuit.name}"
                ),
                "related_circuit_id": circuit.id,
            }
            for location, circuit, premise in location_rows
        )

        circuit_rows = (
            await self.session.execute(
                select(Circuit, ServiceLocation, Asset)
                .join(ServiceLocation, Circuit.service_location_id == ServiceLocation.id)
                .join(Asset, ServiceLocation.asset_id == Asset.id)
                .where(or_(Circuit.id.ilike(pattern), Circuit.name.ilike(pattern)))
                .limit(10)
            )
        ).all()
        results.extend(
            {
                "id": circuit.id,
                "result_type": "circuit",
                "name": circuit.name,
                "subtitle": (
                    f"{location.address} · {premise.metadata_json['serving_lcp_code']} / "
                    f"{premise.metadata_json['splitter_id']} / "
                    f"Port {int(premise.metadata_json['splitter_port']):02d}"
                ),
                "related_circuit_id": circuit.id,
            }
            for circuit, location, premise in circuit_rows
        )

        assets = (
            await self.session.scalars(
                select(Asset)
                .where(
                    Asset.asset_type != "service_location",
                    or_(Asset.id.ilike(pattern), Asset.name.ilike(pattern)),
                )
                .limit(15)
            )
        ).all()
        results.extend(
            {
                "id": asset.id,
                "result_type": "asset",
                "name": asset.name,
                "subtitle": asset.asset_type.replace("_", " ").title(),
            }
            for asset in assets
        )
        return results[:25]

    async def get_asset(self, asset_id: str):
        asset = await self.session.get(Asset, asset_id)
        if not asset:
            raise ProviderNotFoundError(f"Asset {asset_id} was not found")
        return _asset_dict(asset)

    async def get_circuit_path(self, circuit_id: str):
        circuit = await self.session.get(Circuit, circuit_id)
        if not circuit:
            raise ProviderNotFoundError(f"Circuit {circuit_id} was not found")
        location = await self.session.get(ServiceLocation, circuit.service_location_id)
        premise = await self.session.get(Asset, location.asset_id)
        segments = (
            await self.session.scalars(
                select(CircuitPathSegment)
                .where(CircuitPathSegment.circuit_id == circuit_id)
                .order_by(CircuitPathSegment.sequence)
            )
        ).all()
        cable_ids = {segment.cable_id for segment in segments}
        asset_ids = {
            asset_id
            for segment in segments
            for asset_id in (segment.start_asset_id, segment.end_asset_id)
        }
        cables = {
            cable.id: cable
            for cable in (
                await self.session.scalars(select(Cable).where(Cable.id.in_(cable_ids)))
            ).all()
        }
        assets = {
            asset.id: asset
            for asset in (
                await self.session.scalars(select(Asset).where(Asset.id.in_(asset_ids)))
            ).all()
        }
        cumulative = 0.0
        response_segments = []
        for segment in segments:
            cable = cables[segment.cable_id]
            response_segments.append(
                {
                    "sequence": segment.sequence,
                    "cable_id": cable.id,
                    "cable_name": cable.name,
                    "cable_type": cable.cable_type,
                    "start_asset_id": segment.start_asset_id,
                    "end_asset_id": segment.end_asset_id,
                    "start_asset_name": assets[segment.start_asset_id].name,
                    "end_asset_name": assets[segment.end_asset_id].name,
                    "length_ft": segment.length_ft,
                    "cumulative_start_ft": cumulative,
                    "cumulative_end_ft": cumulative + segment.length_ft,
                    "strand_number": segment.strand_number,
                    "coordinates": cable.coordinates,
                }
            )
            cumulative += segment.length_ft
        service_lineage = _service_lineage(location, premise)
        service_leg_segments = next(
            (
                response_segments[index:]
                for index, segment in enumerate(response_segments)
                if segment["start_asset_id"] == service_lineage["lcp_asset_id"]
            ),
            response_segments,
        )
        return {
            "circuit_id": circuit.id,
            "circuit_name": circuit.name,
            "service_location_id": location.id,
            "service_address": location.address,
            "service_lineage": service_lineage,
            "total_length_ft": cumulative,
            "service_leg_start_sequence": service_leg_segments[0]["sequence"],
            "service_leg_length_ft": sum(
                segment["length_ft"] for segment in service_leg_segments
            ),
            "service_leg_segments": service_leg_segments,
            "segments": response_segments,
        }

    async def get_service_path(self, service_location_id: str):
        circuit = await self.session.scalar(
            select(Circuit)
            .where(Circuit.service_location_id == service_location_id)
            .order_by(Circuit.id)
            .limit(1)
        )
        if not circuit:
            raise ProviderNotFoundError(
                f"Active service for address record {service_location_id} was not found"
            )
        return await self.get_circuit_path(circuit.id)

    async def get_assets_nearby(self, latitude: float, longitude: float, radius_ft: float):
        radius_meters = radius_ft * 0.3048
        rows = (
            await self.session.execute(
                text(
                    """
                    SELECT id, name, asset_type, status, latitude, longitude,
                           metadata_json,
                           ST_Distance(
                               location::geography,
                               ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography
                           ) / 0.3048 AS distance_ft
                    FROM assets
                    WHERE ST_DWithin(
                        location::geography,
                        ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography,
                        :radius_meters
                    )
                    ORDER BY distance_ft
                    LIMIT 25
                    """
                ),
                {
                    "latitude": latitude,
                    "longitude": longitude,
                    "radius_meters": radius_meters,
                },
            )
        ).mappings()
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "asset_type": row["asset_type"],
                "status": row["status"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "metadata": row["metadata_json"] or {},
                "distance_ft": round(row["distance_ft"], 1),
            }
            for row in rows
        ]

    async def calculate_outage_impact(self, asset_id: str):
        assets = (await self.session.scalars(select(Asset))).all()
        cables = (await self.session.scalars(select(Cable))).all()
        circuits = (await self.session.scalars(select(Circuit))).all()
        locations = (await self.session.scalars(select(ServiceLocation))).all()
        segments = (await self.session.scalars(select(CircuitPathSegment))).all()
        try:
            return calculate_graph_impact(
                asset_id,
                [_cable_dict(cable) for cable in cables],
                [
                    {
                        "id": circuit.id,
                        "service_location_id": circuit.service_location_id,
                        "alternate_path_available": circuit.alternate_path_available,
                    }
                    for circuit in circuits
                ],
                [
                    {
                        "circuit_id": segment.circuit_id,
                        "cable_id": segment.cable_id,
                        "start_asset_id": segment.start_asset_id,
                        "end_asset_id": segment.end_asset_id,
                        "strand_number": segment.strand_number,
                    }
                    for segment in segments
                ],
                [
                    {
                        "id": location.id,
                        "account_type": location.account_type,
                    }
                    for location in locations
                ],
                {asset.id: asset.asset_type for asset in assets},
            )
        except LookupError as exc:
            raise ProviderNotFoundError(str(exc)) from exc

    async def get_overview(self):
        assets = (await self.session.scalars(select(Asset).order_by(Asset.id))).all()
        cables = (await self.session.scalars(select(Cable).order_by(Cable.id))).all()
        circuit_rows = (
            await self.session.execute(
                select(Circuit, ServiceLocation, Asset)
                .join(ServiceLocation, Circuit.service_location_id == ServiceLocation.id)
                .join(Asset, ServiceLocation.asset_id == Asset.id)
                .order_by(Circuit.id)
            )
        ).all()
        return {
            "assets": [_asset_dict(asset) for asset in assets],
            "cables": [_cable_dict(cable) for cable in cables],
            "circuits": [
                {
                    "id": circuit.id,
                    "name": circuit.name,
                    "service_address": location.address,
                    "service_location_id": location.id,
                    "service_lineage": _service_lineage(location, premise),
                    "status": circuit.status,
                }
                for circuit, location, premise in circuit_rows
            ],
            "incidents": INCIDENTS,
        }
