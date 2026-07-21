import pytest

from app.services.analysis import correlate_otdr


@pytest.mark.asyncio
async def test_route_distance_correlates_to_closure_not_straight_line(provider):
    path = await provider.get_circuit_path("circuit-7001")
    assets = {
        asset_id: await provider.get_asset(asset_id)
        for segment in path["segments"]
        for asset_id in (segment["start_asset_id"], segment["end_asset_id"])
    }
    result = correlate_otdr(path, assets, 18420, 500)

    assert result["nearest_asset"]["id"] == "closure-001"
    assert result["offset_ft"] == 0
    assert result["confidence"] == "high"
    assert result["nearest_cable_segment"]["cable_id"] == "cable-backbone-003"


@pytest.mark.asyncio
async def test_graph_cut_finds_downstream_circuits(provider):
    result = await provider.calculate_outage_impact("cable-backbone-001")

    assert len(result["affected_circuits"]) == 8
    assert "circuit-7001" in result["affected_circuits"]
    assert result["suggested_restoration_priority"].startswith("P1")
