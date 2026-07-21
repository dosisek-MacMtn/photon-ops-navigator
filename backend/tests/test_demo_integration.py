def test_full_high_loss_incident_workflow(client):
    search = client.get("/api/assets/search", params={"q": "DXR-7001"})
    assert search.status_code == 200
    assert search.json()[0]["id"] == "circuit-7001"

    path = client.get("/api/service-locations/service-001/path")
    assert path.status_code == 200
    assert path.json()["segments"][0]["start_asset_id"] == "pop-001"

    payload = {
        "circuit_id": "circuit-7001",
        "launch_asset_id": "pop-001",
        "fault_distance_ft": 18420,
        "tolerance_ft": 500,
    }
    correlation = client.post("/api/analysis/otdr-correlate", json=payload)
    assert correlation.status_code == 200
    body = correlation.json()
    assert body["nearest_asset"]["id"] == "closure-001"
    assert body["confidence"] == "high"

    impact = client.get("/api/analysis/outage-impact/cable-backbone-001")
    assert impact.status_code == 200
    assert len(impact.json()["affected_circuits"]) == 8

    plan = client.post(
        "/api/reports/field-action-plan",
        json={**payload, "impact_asset_id": "cable-backbone-001"},
    )
    assert plan.status_code == 200
    report = plan.json()
    assert report["generated_by"] == "deterministic topology template"
    assert "8 circuit(s)" in report["affected_circuits_and_services"]
    assert len(report["restoration_sequence"]) >= 4


def test_residential_address_resolves_lcp_splitter_port_and_service_leg(client):
    search = client.get("/api/assets/search", params={"q": "43 Main St"})
    assert search.status_code == 200
    address = search.json()[0]
    assert address["result_type"] == "service_location"
    assert address["name"] == "43 Main St, Dexter, ME (DEV)"
    assert address["related_circuit_id"] == "circuit-7001"
    assert "LCP-101 / SPL-01 / Port 01" in address["subtitle"]

    path = client.get("/api/service-locations/service-001/path")
    assert path.status_code == 200
    payload = path.json()
    assert payload["service_lineage"] == {
        "account_type": "residential",
        "premise_asset_id": "service-asset-001",
        "lcp_asset_id": "cabinet-101",
        "lcp_name": "LCP-101 · North Main",
        "lcp_code": "LCP-101",
        "splitter_id": "SPL-01",
        "splitter_ratio": "1:32",
        "splitter_port": 1,
    }
    assert payload["service_leg_start_sequence"] == 2
    assert payload["service_leg_segments"][0]["start_asset_id"] == "cabinet-101"
    assert payload["service_leg_segments"][-1]["end_asset_id"] == "service-asset-001"
    assert payload["service_leg_length_ft"] < payload["total_length_ft"]
