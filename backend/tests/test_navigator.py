def test_guided_intake_queries_provider_and_resolves_circuit(client):
    response = client.post(
        "/api/navigator/intake",
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "High loss on DXR-7001 at 18,420 ft from the OTDR launch",
                }
            ]
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_mode"] == "guided_parser"
    assert payload["provider_label"] == "Demo PostGIS"
    assert payload["provider_queries"] == ["DXR-7001"]
    assert payload["selected_circuit_id"] == "circuit-7001"
    assert payload["fault_distance_ft"] == 18420
    assert payload["status"] == "ready"


def test_otdr_intake_asks_for_missing_distance_after_resolving_circuit(client):
    response = client.post(
        "/api/navigator/intake",
        json={
            "messages": [
                {"role": "user", "content": "Run an OTDR investigation for DXR-7001"}
            ]
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["selected_circuit_id"] == "circuit-7001"
    assert payload["status"] == "needs_input"
    assert "distance" in payload["assistant_message"].lower()


def test_capabilities_do_not_claim_vetro_is_live(client):
    response = client.get("/api/navigator/capabilities")

    assert response.status_code == 200
    assert response.json()["vetro_ready"] is False


def test_guided_intake_accepts_residential_service_address(client):
    response = client.post(
        "/api/navigator/intake",
        json={
            "messages": [
                {"role": "user", "content": "Investigate service at 43 Main St (DEV)"}
            ]
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["selected_circuit_id"] == "circuit-7001"
    assert payload["matches"][0]["result_type"] == "service_location"
    assert payload["matches"][0]["name"] == "43 Main St, Dexter, ME (DEV)"
    assert "LCP-101 / SPL-01 / Port 01" in payload["assistant_message"]
    assert payload["status"] == "ready"
