from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.adapters.base import NetworkDataProvider
from app.config import Settings
from app.services.ai.bedrock_mantle import BedrockMantleNarrativeProvider

CIRCUIT_PATTERN = re.compile(r"\b(?:DXR-\d{4}|circuit-\d+)\b", re.IGNORECASE)
DISTANCE_PATTERN = re.compile(r"\b(\d[\d,]*(?:\.\d+)?)\s*(?:ft|feet|foot)\b", re.IGNORECASE)
TOLERANCE_PATTERN = re.compile(
    r"(?:±|\+/-)\s*(\d[\d,]*(?:\.\d+)?)\s*(?:ft|feet|foot)\b",
    re.IGNORECASE,
)
ADDRESS_PATTERN = re.compile(
    r"\b\d{1,6}\s+[a-z0-9 .'-]+?\s+"
    r"(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|boulevard|blvd)\b",
    re.IGNORECASE,
)


class IntakeIntent(BaseModel):
    goal: Literal["otdr", "outage", "inspect"] = "inspect"
    search_query: str | None = Field(default=None, max_length=120)
    fault_distance_ft: float | None = Field(default=None, gt=0, le=5_000_000)
    tolerance_ft: float = Field(default=500, gt=0, le=5000)


def navigator_capabilities(settings: Settings) -> dict[str, Any]:
    ai_enabled = settings.ai_provider == "bedrock_mantle"
    provider_is_vetro = settings.network_provider == "vetro"
    return {
        "ai_mode": "bedrock_mantle" if ai_enabled else "guided_parser",
        "ai_label": (
            "Amazon Bedrock Mantle · live" if ai_enabled else "Guided demo · AI off"
        ),
        "ai_enabled": ai_enabled,
        "network_provider": settings.network_provider,
        "network_label": "VETRO FiberMap" if provider_is_vetro else "Demo PostGIS",
        # The checked-in adapter is intentionally a contract stub until an approved
        # customer API profile is available. Do not infer readiness from a mode flag.
        "vetro_ready": False,
        "map_label": "Esri World Imagery",
    }


async def run_navigator_intake(
    provider: NetworkDataProvider,
    settings: Settings,
    messages: list[dict[str, str]],
) -> dict[str, Any]:
    capabilities = navigator_capabilities(settings)
    if settings.ai_provider == "bedrock_mantle":
        interpreter = BedrockMantleNarrativeProvider(settings)
        intent = IntakeIntent.model_validate(await interpreter.interpret_intake(messages))
    else:
        intent = parse_guided_intake(messages)

    provider_queries: list[str] = []
    matches: list[dict[str, Any]] = []
    if intent.search_query:
        provider_queries.append(intent.search_query)
        try:
            matches = await provider.search_assets(intent.search_query)
        except NotImplementedError:
            return {
                **_response_identity(capabilities),
                "status": "provider_unavailable",
                "assistant_message": (
                    "I understood the request, but the VETRO connection is not active. "
                    "An approved tenant API profile and token are required before I can "
                    "resolve this against FiberMap."
                ),
                **intent.model_dump(),
                "matches": [],
                "selected_circuit_id": None,
                "provider_queries": provider_queries,
            }

    selected_circuit_id = _select_circuit(matches, intent.search_query)
    selected_match = next(
        (
            item
            for item in matches
            if item.get("related_circuit_id") == selected_circuit_id
        ),
        None,
    )
    status: Literal["needs_input", "ready"] = "ready"
    if not intent.search_query:
        status = "needs_input"
        assistant_message = (
            "Which circuit name or service address should I resolve against the network model?"
        )
    elif not selected_circuit_id:
        status = "needs_input"
        assistant_message = (
            f"I queried {capabilities['network_label']} for “{intent.search_query}” but did not "
            "find a verified circuit. Check the circuit name or provide a service address."
        )
    elif intent.goal == "otdr" and intent.fault_distance_ft is None:
        status = "needs_input"
        assistant_message = (
            "I verified the circuit. What distance from the OTDR launch point should I correlate?"
        )
    else:
        distance_copy = (
            f" and captured {intent.fault_distance_ft:,.0f} ft from the launch point"
            if intent.fault_distance_ft is not None
            else ""
        )
        verified_name = (
            str(selected_match["name"])
            if selected_match and selected_match.get("result_type") == "service_location"
            else selected_circuit_id
        )
        serving_copy = (
            f" ({selected_match['subtitle']})"
            if selected_match and selected_match.get("result_type") == "service_location"
            else ""
        )
        assistant_message = (
            f"Verified {verified_name}{serving_copy} in "
            f"{capabilities['network_label']}{distance_copy}. Open the investigation to "
            "trace the serving LCP splitter port to the address and run deterministic analysis."
        )

    return {
        **_response_identity(capabilities),
        "status": status,
        "assistant_message": assistant_message,
        **intent.model_dump(),
        "matches": matches,
        "selected_circuit_id": selected_circuit_id,
        "provider_queries": provider_queries,
    }


def parse_guided_intake(messages: list[dict[str, str]]) -> IntakeIntent:
    user_text = "\n".join(
        message["content"] for message in messages if message["role"] == "user"
    )
    lowered = user_text.lower()
    if any(token in lowered for token in ("otdr", "reflect", "high loss", "distance")):
        goal: Literal["otdr", "outage", "inspect"] = "otdr"
    elif any(token in lowered for token in ("outage", "cut", "down", "impact")):
        goal = "outage"
    else:
        goal = "inspect"

    circuit_match = CIRCUIT_PATTERN.search(user_text)
    address_match = ADDRESS_PATTERN.search(user_text)
    distance_match = DISTANCE_PATTERN.search(user_text)
    tolerance_match = TOLERANCE_PATTERN.search(user_text)
    query = circuit_match.group(0) if circuit_match else None
    if query is None and address_match:
        query = address_match.group(0)

    return IntakeIntent(
        goal=goal,
        search_query=query,
        fault_distance_ft=_number(distance_match.group(1)) if distance_match else None,
        tolerance_ft=_number(tolerance_match.group(1)) if tolerance_match else 500,
    )


def _number(value: str) -> float:
    return float(value.replace(",", ""))


def _select_circuit(matches: list[dict[str, Any]], query: str | None) -> str | None:
    circuit_matches = [item for item in matches if item.get("result_type") == "circuit"]
    if query:
        normalized = query.lower()
        exact = next(
            (
                item
                for item in circuit_matches
                if normalized
                in {
                    str(item.get("id", "")).lower(),
                    str(item.get("name", "")).lower(),
                }
            ),
            None,
        )
        if exact:
            return str(exact["related_circuit_id"])
    for match in matches:
        if match.get("related_circuit_id"):
            return str(match["related_circuit_id"])
    return None


def _response_identity(capabilities: dict[str, Any]) -> dict[str, Any]:
    return {
        "assistant_mode": capabilities["ai_mode"],
        "assistant_label": capabilities["ai_label"],
        "provider": capabilities["network_provider"],
        "provider_label": capabilities["network_label"],
        "vetro_live": capabilities["vetro_ready"],
    }
