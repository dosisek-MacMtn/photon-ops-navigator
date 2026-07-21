"""Deterministic fictional network used by Docker demos and automated tests."""

from __future__ import annotations

import math
from typing import Any

INCIDENTS = [
    {
        "id": "incident-001",
        "title": "High-loss splice on Main Street feeder",
        "severity": "major",
        "incident_type": "high_loss_splice",
        "circuit_id": "circuit-7001",
        "asset_id": "closure-001",
        "fault_distance_ft": 18420,
        "status": "investigating",
    },
    {
        "id": "incident-002",
        "title": "Reflective event west of closure SC-08",
        "severity": "minor",
        "incident_type": "reflective_event",
        "circuit_id": "circuit-7008",
        "asset_id": "closure-008",
        "fault_distance_ft": 21520,
        "status": "monitoring",
    },
    {
        "id": "incident-003",
        "title": "Backbone cut — north cabinet route",
        "severity": "critical",
        "incident_type": "cable_cut",
        "circuit_id": None,
        "asset_id": "cable-backbone-001",
        "fault_distance_ft": None,
        "status": "dispatching",
    },
]


def _asset(
    asset_id: str,
    name: str,
    asset_type: str,
    lon: float,
    lat: float,
    **metadata: Any,
) -> dict[str, Any]:
    return {
        "id": asset_id,
        "name": name,
        "asset_type": asset_type,
        "status": "active",
        "longitude": round(lon, 6),
        "latitude": round(lat, 6),
        "metadata": metadata,
    }


def _cable(
    cable_id: str,
    name: str,
    cable_type: str,
    start: dict[str, Any],
    end: dict[str, Any],
    length_ft: float,
    fiber_count: int,
    waypoints: list[list[float]] | None = None,
) -> dict[str, Any]:
    coordinates = [[start["longitude"], start["latitude"]]]
    coordinates.extend(waypoints or [])
    coordinates.append([end["longitude"], end["latitude"]])
    return {
        "id": cable_id,
        "name": name,
        "cable_type": cable_type,
        "start_asset_id": start["id"],
        "end_asset_id": end["id"],
        "length_ft": float(length_ft),
        "fiber_count": fiber_count,
        "status": "active",
        "coordinates": coordinates,
    }


def build_demo_network() -> dict[str, Any]:
    assets: list[dict[str, Any]] = []
    assets.append(
        _asset("pop-001", "Dexter Central POP", "pop", -69.2890, 45.0230, code="DXTR-POP")
    )
    assets.extend(
        [
            _asset(
                "cabinet-101",
                "LCP-101 · North Main",
                "lcp",
                -69.2710,
                45.0360,
                lcp_code="LCP-101",
                splitter_ratio="1:32",
                splitters=["SPL-01"],
            ),
            _asset(
                "cabinet-102",
                "LCP-102 · Lake Road",
                "lcp",
                -69.3075,
                45.0105,
                lcp_code="LCP-102",
                splitter_ratio="1:32",
                splitters=["SPL-01"],
            ),
        ]
    )
    closure_coordinates = [
        (-69.2545, 45.0440),
        (-69.2790, 45.0490),
        (-69.2375, 45.0520),
        (-69.2920, 45.0590),
        (-69.3240, 45.0010),
        (-69.2980, 44.9930),
        (-69.3420, 44.9900),
        (-69.2895, 44.9770),
    ]
    for index, (lon, lat) in enumerate(closure_coordinates, start=1):
        assets.append(
            _asset(
                f"closure-{index:03d}",
                f"Splice Closure SC-{index:02d}",
                "splice_closure",
                lon,
                lat,
                tray_count=4,
            )
        )

    asset_map = {item["id"]: item for item in assets}
    pole_counts = [4, 4, 4, 4, 4, 4, 3, 3]
    poles_by_closure: dict[str, list[str]] = {}
    pole_number = 1
    for closure_index, count in enumerate(pole_counts, start=1):
        closure_id = f"closure-{closure_index:03d}"
        closure = asset_map[closure_id]
        poles_by_closure[closure_id] = []
        direction = 1 if closure_index % 2 else -1
        for local_index in range(count):
            angle = (closure_index * 0.61) + local_index * 0.28
            distance = 0.0042 + local_index * 0.0030
            lon = closure["longitude"] + math.cos(angle) * distance * direction
            lat = closure["latitude"] + math.sin(angle) * distance
            pole_id = f"pole-{pole_number:03d}"
            pole = _asset(
                pole_id,
                f"Pole P-{pole_number:03d}",
                "pole",
                lon,
                lat,
                pole_class="40-4",
            )
            assets.append(pole)
            asset_map[pole_id] = pole
            poles_by_closure[closure_id].append(pole_id)
            pole_number += 1

    cables: list[dict[str, Any]] = []
    backbone_specs = [
        ("001", "pop-001", "cabinet-101", 12500),
        ("002", "pop-001", "cabinet-102", 11800),
        ("003", "cabinet-101", "closure-001", 5920),
        ("004", "cabinet-101", "closure-002", 6500),
        ("005", "cabinet-102", "closure-005", 5400),
        ("006", "cabinet-102", "closure-006", 6100),
    ]
    for suffix, start_id, end_id, length in backbone_specs:
        cables.append(
            _cable(
                f"cable-backbone-{suffix}",
                f"Backbone BB-{suffix}",
                "backbone",
                asset_map[start_id],
                asset_map[end_id],
                length,
                288,
            )
        )

    bridge_specs = [
        ("001", "closure-001", "closure-003", 4100),
        ("002", "closure-002", "closure-004", 3900),
        ("003", "closure-005", "closure-007", 4300),
        ("004", "closure-006", "closure-008", 3800),
    ]
    for suffix, start_id, end_id, length in bridge_specs:
        cables.append(
            _cable(
                f"cable-distribution-{suffix}",
                f"Distribution Link DL-{suffix}",
                "distribution",
                asset_map[start_id],
                asset_map[end_id],
                length,
                144,
            )
        )

    feeder_by_pole: dict[str, str] = {}
    terminal_poles_by_closure: dict[str, list[str]] = {}
    distribution_number = 5
    for closure_index in range(1, 9):
        closure_id = f"closure-{closure_index:03d}"
        pole_ids = poles_by_closure[closure_id]
        terminal_poles_by_closure[closure_id] = []
        split_at = max(1, math.ceil(len(pole_ids) / 2))
        for group in (pole_ids[:split_at], pole_ids[split_at:]):
            if not group:
                group = pole_ids[-1:]
            end_id = group[-1]
            waypoints = [
                [asset_map[pole_id]["longitude"], asset_map[pole_id]["latitude"]]
                for pole_id in group[:-1]
            ]
            cable_id = f"cable-distribution-{distribution_number:03d}"
            cables.append(
                _cable(
                    cable_id,
                    f"Distribution Feeder DF-{distribution_number:03d}",
                    "distribution",
                    asset_map[closure_id],
                    asset_map[end_id],
                    3600 + (distribution_number * 85),
                    144,
                    waypoints,
                )
            )
            for pole_id in group:
                feeder_by_pole[pole_id] = cable_id
            terminal_poles_by_closure[closure_id].append(end_id)
            distribution_number += 1

    routes_to_closure = {
        "closure-001": ["cable-backbone-001", "cable-backbone-003"],
        "closure-002": ["cable-backbone-001", "cable-backbone-004"],
        "closure-003": ["cable-backbone-001", "cable-backbone-003", "cable-distribution-001"],
        "closure-004": ["cable-backbone-001", "cable-backbone-004", "cable-distribution-002"],
        "closure-005": ["cable-backbone-002", "cable-backbone-005"],
        "closure-006": ["cable-backbone-002", "cable-backbone-006"],
        "closure-007": ["cable-backbone-002", "cable-backbone-005", "cable-distribution-003"],
        "closure-008": ["cable-backbone-002", "cable-backbone-006", "cable-distribution-004"],
    }

    service_locations: list[dict[str, Any]] = []
    service_drop_by_location: dict[str, str] = {}
    closure_by_service: dict[str, str] = {}
    pole_by_service: dict[str, str] = {}
    lcp_by_closure = {
        **{f"closure-{index:03d}": "cabinet-101" for index in range(1, 5)},
        **{f"closure-{index:03d}": "cabinet-102" for index in range(5, 9)},
    }
    next_splitter_port = {"cabinet-101": 1, "cabinet-102": 1}
    street_names = ["Main St", "Maple Ave", "Lake Rd", "Church St", "Spring St"]
    for index in range(50):
        number = index + 1
        closure_id = f"closure-{(index % 8) + 1:03d}"
        pole_ids = terminal_poles_by_closure[closure_id]
        pole_id = pole_ids[(index // 8) % len(pole_ids)]
        pole = asset_map[pole_id]
        lon = pole["longitude"] + (0.00055 if index % 2 else -0.00045)
        lat = pole["latitude"] + (0.00032 if index % 3 else -0.00038)
        asset_id = f"service-asset-{number:03d}"
        location_id = f"service-{number:03d}"
        address = (
            f"{40 + number * 3} {street_names[index % len(street_names)]}, "
            "Dexter, ME (DEV)"
        )
        lcp_id = lcp_by_closure[closure_id]
        splitter_port = next_splitter_port[lcp_id]
        next_splitter_port[lcp_id] += 1
        lcp_code = asset_map[lcp_id]["metadata"]["lcp_code"]
        service_asset = _asset(
            asset_id,
            address,
            "service_location",
            lon,
            lat,
            service_location_id=location_id,
            premise_id=f"PREM-{number:04d}",
            serving_lcp_id=lcp_id,
            serving_lcp_name=asset_map[lcp_id]["name"],
            serving_lcp_code=lcp_code,
            splitter_id="SPL-01",
            splitter_ratio="1:32",
            splitter_port=splitter_port,
        )
        assets.append(service_asset)
        asset_map[asset_id] = service_asset
        account_type = "business" if number in {3, 9, 14, 22, 31, 42} else "residential"
        service_locations.append(
            {
                "id": location_id,
                "asset_id": asset_id,
                "name": f"Subscriber {number:03d} (DEV)",
                "address": address,
                "account_type": account_type,
                "latitude": service_asset["latitude"],
                "longitude": service_asset["longitude"],
            }
        )
        drop_id = f"cable-drop-{number:03d}"
        cables.append(
            _cable(
                drop_id,
                f"Service Drop SD-{number:03d}",
                "service_drop",
                pole,
                service_asset,
                260 + (index % 7) * 42,
                2,
            )
        )
        service_drop_by_location[location_id] = drop_id
        closure_by_service[location_id] = closure_id
        pole_by_service[location_id] = pole_id

    cable_map = {item["id"]: item for item in cables}
    circuits: list[dict[str, Any]] = []
    path_segments: list[dict[str, Any]] = []
    for index in range(15):
        circuit_number = 7001 + index
        circuit_id = f"circuit-{circuit_number}"
        service = service_locations[index]
        closure_id = closure_by_service[service["id"]]
        pole_id = pole_by_service[service["id"]]
        cable_ids = [
            *routes_to_closure[closure_id],
            feeder_by_pole[pole_id],
            service_drop_by_location[service["id"]],
        ]
        circuits.append(
            {
                "id": circuit_id,
                "name": f"DXR-{circuit_number}",
                "service_location_id": service["id"],
                "status": "active",
                "alternate_path_available": circuit_number in {7006, 7012},
            }
        )
        for sequence, cable_id in enumerate(cable_ids, start=1):
            cable = cable_map[cable_id]
            path_segments.append(
                {
                    "circuit_id": circuit_id,
                    "cable_id": cable_id,
                    "sequence": sequence,
                    "start_asset_id": cable["start_asset_id"],
                    "end_asset_id": cable["end_asset_id"],
                    "length_ft": cable["length_ft"],
                    "strand_number": index + 1,
                }
            )

    return {
        "assets": assets,
        "cables": cables,
        "service_locations": service_locations,
        "circuits": circuits,
        "path_segments": path_segments,
        "incidents": INCIDENTS,
    }
