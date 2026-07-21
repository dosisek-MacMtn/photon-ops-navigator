from __future__ import annotations

from typing import Any


def _interpolate(coordinates: list[list[float]], fraction: float) -> tuple[float, float]:
    if len(coordinates) < 2:
        lon, lat = coordinates[0]
        return lat, lon
    fraction = max(0.0, min(1.0, fraction))
    scaled = fraction * (len(coordinates) - 1)
    index = min(int(scaled), len(coordinates) - 2)
    local = scaled - index
    lon1, lat1 = coordinates[index]
    lon2, lat2 = coordinates[index + 1]
    return lat1 + (lat2 - lat1) * local, lon1 + (lon2 - lon1) * local


def correlate_otdr(
    path: dict[str, Any],
    assets: dict[str, dict[str, Any]],
    fault_distance_ft: float,
    tolerance_ft: float,
) -> dict[str, Any]:
    if not path["segments"]:
        raise ValueError("Circuit has no mapped path segments")

    total_length = path["total_length_ft"]
    clamped_distance = min(fault_distance_ft, total_length)
    segment = path["segments"][-1]
    for candidate in path["segments"]:
        if clamped_distance <= candidate["cumulative_end_ft"]:
            segment = candidate
            break

    distance_into_segment = max(0.0, clamped_distance - segment["cumulative_start_ft"])
    distance_to_end = max(0.0, segment["length_ft"] - distance_into_segment)
    if distance_into_segment <= distance_to_end:
        nearest_asset_id = segment["start_asset_id"]
        offset_ft = distance_into_segment
    else:
        nearest_asset_id = segment["end_asset_id"]
        offset_ft = distance_to_end

    if fault_distance_ft > total_length or offset_ft > tolerance_ft:
        confidence = "low"
    elif offset_ft <= tolerance_ft * 0.25:
        confidence = "high"
    else:
        confidence = "medium"

    fraction = distance_into_segment / segment["length_ft"] if segment["length_ft"] else 0
    latitude, longitude = _interpolate(segment["coordinates"], fraction)
    nearest_asset = assets[nearest_asset_id]
    return {
        "nearest_asset": nearest_asset,
        "nearest_cable_segment": segment,
        "offset_ft": round(offset_ft, 1),
        "confidence": confidence,
        "affected_circuit": path["circuit_id"],
        "fault_distance_ft": fault_distance_ft,
        "path_length_ft": total_length,
        "recommended_field_search_area": {
            "latitude": round(latitude, 6),
            "longitude": round(longitude, 6),
            "radius_ft": tolerance_ft,
            "instruction": (
                f"Search {tolerance_ft:.0f} ft along {segment['cable_name']} around "
                f"{nearest_asset['name']}."
            ),
        },
    }
