export type Asset = {
  id: string;
  name: string;
  asset_type: string;
  status: string;
  latitude: number;
  longitude: number;
  metadata: Record<string, unknown>;
};

export type Cable = {
  id: string;
  name: string;
  cable_type: "backbone" | "distribution" | "service_drop" | string;
  start_asset_id: string;
  end_asset_id: string;
  length_ft: number;
  fiber_count: number;
  status: string;
  coordinates: number[][];
};

export type ServiceLineage = {
  account_type: "residential" | "business";
  premise_asset_id: string;
  lcp_asset_id: string;
  lcp_name: string;
  lcp_code: string;
  splitter_id: string;
  splitter_ratio: string;
  splitter_port: number;
};

export type CircuitSummary = {
  id: string;
  name: string;
  service_address: string;
  service_location_id: string;
  service_lineage: ServiceLineage;
  status: string;
};

export type Incident = {
  id: string;
  title: string;
  severity: "critical" | "major" | "minor";
  incident_type: string;
  circuit_id: string | null;
  asset_id: string;
  fault_distance_ft: number | null;
  status: string;
};

export type DemoOverview = {
  assets: Asset[];
  cables: Cable[];
  circuits: CircuitSummary[];
  incidents: Incident[];
};

export type PathSegment = {
  sequence: number;
  cable_id: string;
  cable_name: string;
  cable_type: string;
  start_asset_id: string;
  end_asset_id: string;
  start_asset_name: string;
  end_asset_name: string;
  length_ft: number;
  cumulative_start_ft: number;
  cumulative_end_ft: number;
  strand_number: number;
  coordinates: number[][];
};

export type CircuitPath = {
  circuit_id: string;
  circuit_name: string;
  service_location_id: string;
  service_address: string;
  service_lineage: ServiceLineage;
  total_length_ft: number;
  service_leg_start_sequence: number;
  service_leg_length_ft: number;
  service_leg_segments: PathSegment[];
  segments: PathSegment[];
};

export type SearchResult = {
  id: string;
  result_type: "asset" | "circuit" | "service_location";
  name: string;
  subtitle: string;
  related_circuit_id?: string | null;
};

export type NavigatorMessage = {
  role: "user" | "assistant";
  content: string;
};

export type NavigatorCapabilities = {
  ai_mode: "guided_parser" | "bedrock_mantle";
  ai_label: string;
  ai_enabled: boolean;
  network_provider: "demo" | "vetro";
  network_label: string;
  vetro_ready: boolean;
  map_label: string;
};

export type NavigatorIntake = {
  assistant_mode: "guided_parser" | "bedrock_mantle";
  assistant_label: string;
  provider: "demo" | "vetro";
  provider_label: string;
  vetro_live: boolean;
  status: "needs_input" | "ready" | "provider_unavailable";
  assistant_message: string;
  goal: "otdr" | "outage" | "inspect";
  search_query: string | null;
  fault_distance_ft: number | null;
  tolerance_ft: number;
  matches: SearchResult[];
  selected_circuit_id: string | null;
  provider_queries: string[];
};

export type Correlation = {
  nearest_asset: Asset;
  nearest_cable_segment: PathSegment;
  offset_ft: number;
  confidence: "high" | "medium" | "low";
  affected_circuit: string;
  fault_distance_ft: number;
  path_length_ft: number;
  recommended_field_search_area: {
    latitude: number;
    longitude: number;
    radius_ft: number;
    instruction: string;
  };
};

export type OutageImpact = {
  asset_id: string;
  asset_type: string;
  affected_circuits: string[];
  affected_service_locations: string[];
  business_accounts_affected: number;
  residential_accounts_affected: number;
  affected_fiber_strands: string[];
  available_alternate_paths: string[];
  suggested_restoration_priority: string;
};

export type FieldPlan = {
  plan_id: string;
  generated_by: string;
  suspected_fault_location: string;
  nearest_mapped_assets: string[];
  affected_circuits_and_services: string;
  recommended_crew_type: string;
  recommended_test_points: string[];
  likely_materials: string[];
  safety_considerations: string[];
  restoration_sequence: string[];
  confidence_and_assumptions: string;
  executive_summary: string | null;
};
