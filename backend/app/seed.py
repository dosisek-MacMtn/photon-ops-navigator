from __future__ import annotations

import argparse
import asyncio
from datetime import datetime

from geoalchemy2.elements import WKTElement
from sqlalchemy import delete, func, select

from app.database import SessionLocal
from app.demo_data import build_demo_network
from app.models import (
    Asset,
    Cable,
    Circuit,
    CircuitPathSegment,
    FiberStrand,
    OTDREvent,
    OTDRTest,
    ServiceLocation,
)


async def seed_database(force: bool = False) -> None:
    data = build_demo_network()
    async with SessionLocal() as session:
        existing = await session.scalar(select(func.count()).select_from(Asset))
        if existing and not force:
            print(f"Demo network already seeded ({existing} assets).")
            return
        if force:
            for model in (
                OTDREvent,
                OTDRTest,
                CircuitPathSegment,
                Circuit,
                FiberStrand,
                Cable,
                ServiceLocation,
                Asset,
            ):
                await session.execute(delete(model))

        for item in data["assets"]:
            session.add(
                Asset(
                    id=item["id"],
                    name=item["name"],
                    asset_type=item["asset_type"],
                    status=item["status"],
                    latitude=item["latitude"],
                    longitude=item["longitude"],
                    location=WKTElement(
                        f"POINT({item['longitude']} {item['latitude']})", srid=4326
                    ),
                    metadata_json=item["metadata"],
                )
            )
        await session.flush()

        for item in data["service_locations"]:
            session.add(ServiceLocation(**item))
        await session.flush()

        for item in data["cables"]:
            line = ", ".join(f"{lon} {lat}" for lon, lat in item["coordinates"])
            session.add(
                Cable(
                    id=item["id"],
                    name=item["name"],
                    cable_type=item["cable_type"],
                    start_asset_id=item["start_asset_id"],
                    end_asset_id=item["end_asset_id"],
                    length_ft=item["length_ft"],
                    fiber_count=item["fiber_count"],
                    status=item["status"],
                    geometry=WKTElement(f"LINESTRING({line})", srid=4326),
                    coordinates=item["coordinates"],
                )
            )
        await session.flush()

        for item in data["circuits"]:
            session.add(Circuit(**item))
        await session.flush()

        allocated_strands: set[tuple[str, int]] = set()
        for item in data["path_segments"]:
            session.add(CircuitPathSegment(**item))
            key = (item["cable_id"], item["strand_number"])
            if key not in allocated_strands:
                allocated_strands.add(key)
                session.add(
                    FiberStrand(
                        id=f"{item['cable_id']}:strand-{item['strand_number']}",
                        cable_id=item["cable_id"],
                        strand_number=item["strand_number"],
                        status="assigned",
                    )
                )

        session.add_all(
            [
                OTDRTest(
                    id="otdr-test-001",
                    circuit_id="circuit-7001",
                    launch_asset_id="pop-001",
                    tested_at=datetime.fromisoformat("2026-07-20T14:05:00+00:00"),
                    wavelength_nm=1550,
                    pulse_width_ns=100,
                    notes="Known high-loss splice demo incident",
                ),
                OTDRTest(
                    id="otdr-test-002",
                    circuit_id="circuit-7008",
                    launch_asset_id="pop-001",
                    tested_at=datetime.fromisoformat("2026-07-20T15:20:00+00:00"),
                    wavelength_nm=1625,
                    pulse_width_ns=200,
                    notes="Known reflective event demo incident",
                ),
            ]
        )
        await session.flush()
        session.add_all(
            [
                OTDREvent(
                    id="otdr-event-001",
                    test_id="otdr-test-001",
                    event_type="high_loss_splice",
                    distance_ft=18420,
                    loss_db=2.7,
                    reflectance_db=None,
                    known_incident=True,
                ),
                OTDREvent(
                    id="otdr-event-002",
                    test_id="otdr-test-002",
                    event_type="reflective_event",
                    distance_ft=21520,
                    loss_db=0.8,
                    reflectance_db=-31.5,
                    known_incident=True,
                ),
            ]
        )
        await session.commit()
        print(
            "Seeded deterministic network: "
            f"{len(data['assets'])} assets, {len(data['cables'])} cables, "
            f"{len(data['circuits'])} circuits."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the Photon-Ops demo network")
    parser.add_argument("--force", action="store_true", help="Replace existing demo data")
    args = parser.parse_args()
    asyncio.run(seed_database(force=args.force))


if __name__ == "__main__":
    main()
