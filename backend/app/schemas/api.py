from typing import Any, Literal

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    id: str
    result_type: Literal["asset", "circuit", "service_location"]
    name: str
    subtitle: str
    related_circuit_id: str | None = None


class NavigatorMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=1200)


class NavigatorIntakeRequest(BaseModel):
    messages: list[NavigatorMessage] = Field(min_length=1, max_length=12)


class NavigatorCapabilitiesResponse(BaseModel):
    ai_mode: Literal["guided_parser", "bedrock_mantle"]
    ai_label: str
    ai_enabled: bool
    network_provider: Literal["demo", "vetro"]
    network_label: str
    vetro_ready: bool
    map_label: str


class NavigatorIntakeResponse(BaseModel):
    assistant_mode: Literal["guided_parser", "bedrock_mantle"]
    assistant_label: str
    provider: Literal["demo", "vetro"]
    provider_label: str
    vetro_live: bool
    status: Literal["needs_input", "ready", "provider_unavailable"]
    assistant_message: str
    goal: Literal["otdr", "outage", "inspect"]
    search_query: str | None = None
    fault_distance_ft: float | None = None
    tolerance_ft: float = 500
    matches: list[SearchResult] = Field(default_factory=list)
    selected_circuit_id: str | None = None
    provider_queries: list[str] = Field(default_factory=list)


class AssetResponse(BaseModel):
    id: str
    name: str
    asset_type: str
    status: str
    latitude: float
    longitude: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class CableResponse(BaseModel):
    id: str
    name: str
    cable_type: str
    start_asset_id: str
    end_asset_id: str
    length_ft: float
    fiber_count: int
    status: str
    coordinates: list[list[float]]


class NearbyAssetResponse(AssetResponse):
    distance_ft: float


class PathSegmentResponse(BaseModel):
    sequence: int
    cable_id: str
    cable_name: str
    cable_type: str
    start_asset_id: str
    end_asset_id: str
    start_asset_name: str
    end_asset_name: str
    length_ft: float
    cumulative_start_ft: float
    cumulative_end_ft: float
    strand_number: int
    coordinates: list[list[float]]


class ServiceLineageResponse(BaseModel):
    account_type: Literal["residential", "business"]
    premise_asset_id: str
    lcp_asset_id: str
    lcp_name: str
    lcp_code: str
    splitter_id: str
    splitter_ratio: str
    splitter_port: int = Field(ge=1)


class CircuitPathResponse(BaseModel):
    circuit_id: str
    circuit_name: str
    service_location_id: str
    service_address: str
    service_lineage: ServiceLineageResponse
    total_length_ft: float
    service_leg_start_sequence: int = Field(ge=1)
    service_leg_length_ft: float = Field(ge=0)
    service_leg_segments: list[PathSegmentResponse]
    segments: list[PathSegmentResponse]


class OTDRCorrelationRequest(BaseModel):
    circuit_id: str
    launch_asset_id: str
    fault_distance_ft: float = Field(gt=0)
    tolerance_ft: float = Field(default=500, gt=0, le=5000)


class SearchArea(BaseModel):
    latitude: float
    longitude: float
    radius_ft: float
    instruction: str


class OTDRCorrelationResponse(BaseModel):
    nearest_asset: AssetResponse
    nearest_cable_segment: PathSegmentResponse
    offset_ft: float
    confidence: Literal["high", "medium", "low"]
    affected_circuit: str
    fault_distance_ft: float
    path_length_ft: float
    recommended_field_search_area: SearchArea


class OutageImpactResponse(BaseModel):
    asset_id: str
    asset_type: str
    affected_circuits: list[str]
    affected_service_locations: list[str]
    business_accounts_affected: int
    residential_accounts_affected: int
    affected_fiber_strands: list[str]
    available_alternate_paths: list[str]
    suggested_restoration_priority: str


class FieldActionPlanRequest(BaseModel):
    circuit_id: str
    launch_asset_id: str
    fault_distance_ft: float = Field(gt=0)
    tolerance_ft: float = Field(default=500, gt=0, le=5000)
    impact_asset_id: str | None = None


class FieldActionPlanResponse(BaseModel):
    plan_id: str
    generated_by: str
    suspected_fault_location: str
    nearest_mapped_assets: list[str]
    affected_circuits_and_services: str
    recommended_crew_type: str
    recommended_test_points: list[str]
    likely_materials: list[str]
    safety_considerations: list[str]
    restoration_sequence: list[str]
    confidence_and_assumptions: str
    executive_summary: str | None = None


class IncidentResponse(BaseModel):
    id: str
    title: str
    severity: Literal["critical", "major", "minor"]
    incident_type: str
    circuit_id: str | None = None
    asset_id: str
    fault_distance_ft: float | None = None
    status: str


class CircuitSummary(BaseModel):
    id: str
    name: str
    service_address: str
    service_location_id: str
    service_lineage: ServiceLineageResponse
    status: str


class DemoOverviewResponse(BaseModel):
    assets: list[AssetResponse]
    cables: list[CableResponse]
    circuits: list[CircuitSummary]
    incidents: list[IncidentResponse]
