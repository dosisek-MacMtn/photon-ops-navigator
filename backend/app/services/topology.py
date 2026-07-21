from __future__ import annotations

from collections import defaultdict, deque
from typing import Any


def calculate_graph_impact(
    target_id: str,
    cables: list[dict[str, Any]],
    circuits: list[dict[str, Any]],
    path_segments: list[dict[str, Any]],
    service_locations: list[dict[str, Any]],
    asset_types: dict[str, str],
) -> dict[str, Any]:
    cable_by_id = {cable["id"]: cable for cable in cables}
    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for cable in cables:
        outgoing[cable["start_asset_id"]].append(cable)

    if target_id in cable_by_id:
        target_type = "cable"
        initial_cables = [cable_by_id[target_id]]
    elif target_id in asset_types:
        target_type = asset_types[target_id]
        initial_cables = list(outgoing.get(target_id, []))
    else:
        raise LookupError(f"Unknown impact target: {target_id}")

    impacted_cable_ids: set[str] = set()
    visited_assets: set[str] = set()
    queue: deque[dict[str, Any]] = deque(initial_cables)
    while queue:
        cable = queue.popleft()
        if cable["id"] in impacted_cable_ids:
            continue
        impacted_cable_ids.add(cable["id"])
        end_asset = cable["end_asset_id"]
        if end_asset in visited_assets:
            continue
        visited_assets.add(end_asset)
        queue.extend(outgoing.get(end_asset, []))

    segments_by_circuit: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for segment in path_segments:
        segments_by_circuit[segment["circuit_id"]].append(segment)

    affected_circuit_ids: list[str] = []
    for circuit in circuits:
        segments = segments_by_circuit.get(circuit["id"], [])
        touches_target_asset = any(
            target_id in {segment["start_asset_id"], segment["end_asset_id"]}
            for segment in segments
        )
        if touches_target_asset or any(
            segment["cable_id"] in impacted_cable_ids for segment in segments
        ):
            affected_circuit_ids.append(circuit["id"])

    circuits_by_id = {circuit["id"]: circuit for circuit in circuits}
    locations_by_id = {location["id"]: location for location in service_locations}
    affected_locations = [
        locations_by_id[circuits_by_id[circuit_id]["service_location_id"]]
        for circuit_id in affected_circuit_ids
    ]
    strand_ids = sorted(
        {
            f"{segment['cable_id']}:strand-{segment['strand_number']}"
            for circuit_id in affected_circuit_ids
            for segment in segments_by_circuit[circuit_id]
            if segment["cable_id"] in impacted_cable_ids
            or target_id in {segment["start_asset_id"], segment["end_asset_id"]}
        }
    )
    alternate_paths = sorted(
        circuit_id
        for circuit_id in affected_circuit_ids
        if circuits_by_id[circuit_id].get("alternate_path_available")
    )
    affected_count = len(affected_circuit_ids)
    if target_type in {"pop", "cabinet"} or affected_count >= 8:
        priority = "P1 — dispatch immediately; broad network impact"
    elif affected_count >= 3:
        priority = "P2 — dispatch within 30 minutes; multi-customer impact"
    else:
        priority = "P3 — schedule targeted repair; limited impact"

    return {
        "asset_id": target_id,
        "asset_type": target_type,
        "affected_circuits": sorted(affected_circuit_ids),
        "affected_service_locations": sorted(item["id"] for item in affected_locations),
        "business_accounts_affected": sum(
            item["account_type"] == "business" for item in affected_locations
        ),
        "residential_accounts_affected": sum(
            item["account_type"] == "residential" for item in affected_locations
        ),
        "affected_fiber_strands": strand_ids,
        "available_alternate_paths": alternate_paths,
        "suggested_restoration_priority": priority,
    }
