from __future__ import annotations

import hashlib
from typing import Any

from app.adapters.base import NetworkDataProvider
from app.config import Settings
from app.services.ai.bedrock_mantle import BedrockMantleNarrativeProvider
from app.services.analysis import correlate_otdr


async def build_field_action_plan(
    provider: NetworkDataProvider,
    settings: Settings,
    circuit_id: str,
    launch_asset_id: str,
    fault_distance_ft: float,
    tolerance_ft: float,
    impact_asset_id: str | None = None,
) -> dict[str, Any]:
    path = await provider.get_circuit_path(circuit_id)
    asset_ids = {
        asset_id
        for segment in path["segments"]
        for asset_id in (segment["start_asset_id"], segment["end_asset_id"])
    }
    assets = {asset_id: await provider.get_asset(asset_id) for asset_id in asset_ids}
    correlation = correlate_otdr(path, assets, fault_distance_ft, tolerance_ft)
    target_id = impact_asset_id or correlation["nearest_cable_segment"]["cable_id"]
    impact = await provider.calculate_outage_impact(target_id)
    area = correlation["recommended_field_search_area"]
    nearby = await provider.get_assets_nearby(area["latitude"], area["longitude"], tolerance_ft)
    nearest_names = [asset["name"] for asset in nearby[:3]]
    if correlation["nearest_asset"]["name"] not in nearest_names:
        nearest_names.insert(0, correlation["nearest_asset"]["name"])

    segment = correlation["nearest_cable_segment"]
    is_backbone = segment["cable_type"] == "backbone"
    plan_key = f"{circuit_id}:{fault_distance_ft}:{target_id}"
    plan = {
        "plan_id": f"FAP-{hashlib.sha256(plan_key.encode()).hexdigest()[:8].upper()}",
        "generated_by": "deterministic topology template",
        "suspected_fault_location": (
            f"{segment['cable_name']}, {correlation['offset_ft']:.0f} ft from "
            f"{correlation['nearest_asset']['name']}"
        ),
        "nearest_mapped_assets": nearest_names[:4],
        "affected_circuits_and_services": (
            f"{len(impact['affected_circuits'])} circuit(s), "
            f"{len(impact['affected_service_locations'])} service location(s): "
            f"{impact['business_accounts_affected']} business and "
            f"{impact['residential_accounts_affected']} residential."
        ),
        "recommended_crew_type": (
            "Two-person emergency OSP splice crew with traffic control"
            if is_backbone or len(impact["affected_circuits"]) >= 3
            else "Two-person OSP maintenance crew"
        ),
        "recommended_test_points": [
            f"Launch OTDR at {launch_asset_id}",
            f"Bidirectional test at {correlation['nearest_asset']['name']}",
            f"Verify light levels toward {path['service_address']}",
        ],
        "likely_materials": (
            ["288-count splice closure kit", "single-mode splice sleeves", "buffer tube repair kit"]
            if is_backbone
            else ["splice closure consumables", "single-mode splice sleeves", "fiber cleaning kit"]
        ),
        "safety_considerations": [
            "Confirm utility locates and traffic-control requirements before excavation.",
            "Treat all fibers as active; verify with an optical power meter before handling.",
            "Use approved ladder, bucket, and roadside work-zone procedures for the mapped plant.",
        ],
        "restoration_sequence": [
            "Confirm the event from the launch point and record the fresh trace.",
            "Inspect the mapped search area and isolate the damaged cable or splice tray.",
            "Protect business and alternate-path circuits before cutting or resplicing.",
            "Repair, perform bidirectional acceptance tests, and restore circuits by priority.",
            "Update the incident record and capture redlines for the system of record.",
        ],
        "confidence_and_assumptions": (
            f"{correlation['confidence'].title()} confidence. Correlation uses ordered route "
            f"distance, a ±{tolerance_ft:.0f} ft tolerance, and the deterministic demo "
            "topology; field conditions and cable slack can shift the physical location."
        ),
        "executive_summary": None,
    }

    if settings.ai_provider == "bedrock_mantle":
        narrative = BedrockMantleNarrativeProvider(settings)
        plan["executive_summary"] = await narrative.summarize(plan)
        plan["generated_by"] += " + Amazon Bedrock Mantle"
    return plan
