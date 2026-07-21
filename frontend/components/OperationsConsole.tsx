"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Bot,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  Crosshair,
  Database,
  LocateFixed,
  LogOut,
  Map as MapIcon,
  MapPin,
  Radio,
  Search,
  ShieldCheck,
  Sparkles,
  UserRound,
  Users,
  Waves,
  XCircle,
  Zap,
} from "lucide-react";
import dynamic from "next/dynamic";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { NavigatorIntake as NavigatorIntakeResult, Incident, SearchResult } from "@/types/network";
import { NavigatorIntake } from "./NavigatorIntake";
import { PhotonBenchWorkspace } from "./PhotonBenchWorkspace";

const MapView = dynamic(() => import("./MapView").then((module) => module.MapView), {
  ssr: false,
  loading: () => <div className="map-loading">Calibrating network trace…</div>,
});

const number = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });

export function OperationsConsole() {
  const auth = useAuth();
  const searchInputRef = useRef<HTMLInputElement>(null);
  const [activeWorkspace, setActiveWorkspace] = useState<"intake" | "operations" | "bench">("intake");
  const [selectedCircuit, setSelectedCircuit] = useState("circuit-7001");
  const [faultDistance, setFaultDistance] = useState(18420);
  const [tolerance, setTolerance] = useState(500);
  const [searchQuery, setSearchQuery] = useState("");
  const [layers, setLayers] = useState({ satellite: true, backbone: true, distribution: true, drops: false, assets: true });

  const overview = useQuery({ queryKey: ["overview"], queryFn: api.overview });
  const capabilities = useQuery({ queryKey: ["navigator-capabilities"], queryFn: api.navigatorCapabilities });
  const selectedCircuitSummary = useMemo(
    () => overview.data?.circuits.find((circuit) => circuit.id === selectedCircuit),
    [overview.data, selectedCircuit],
  );
  const selectedServiceLocationId = selectedCircuitSummary?.service_location_id;
  const path = useQuery({
    queryKey: ["service-path", selectedServiceLocationId],
    queryFn: () => api.servicePath(selectedServiceLocationId!),
    enabled: Boolean(selectedServiceLocationId),
  });
  const search = useQuery({
    queryKey: ["search", searchQuery],
    queryFn: () => api.search(searchQuery),
    enabled: searchQuery.trim().length >= 2,
  });
  const impact = useMutation({ mutationFn: api.outageImpact });
  const correlation = useMutation({
    mutationFn: api.correlate,
    onSuccess: (result) => impact.mutate(result.nearest_cable_segment.cable_id),
  });
  const fieldPlan = useMutation({ mutationFn: api.fieldPlan });

  const workspaceLabel = {
    intake: "Navigator intake",
    operations: "Plant operations",
    bench: "Photon Bench",
  }[activeWorkspace];

  useEffect(() => {
    function focusSearch(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setActiveWorkspace("operations");
        window.setTimeout(() => searchInputRef.current?.focus(), 0);
      }
    }
    window.addEventListener("keydown", focusSearch);
    return () => window.removeEventListener("keydown", focusSearch);
  }, []);

  function chooseCircuit(circuitId: string, incidentDistance?: number | null) {
    setSelectedCircuit(circuitId);
    if (incidentDistance) setFaultDistance(incidentDistance);
    correlation.reset();
    impact.reset();
    fieldPlan.reset();
  }

  function chooseIncident(incident: Incident) {
    if (incident.circuit_id) chooseCircuit(incident.circuit_id, incident.fault_distance_ft);
    if (incident.incident_type === "cable_cut") impact.mutate(incident.asset_id);
  }

  function chooseSearchResult(result: SearchResult) {
    const circuitId = result.result_type === "circuit" ? result.id : result.related_circuit_id;
    if (circuitId) chooseCircuit(circuitId);
    setSearchQuery("");
  }

  function openNavigatorInvestigation(intake: NavigatorIntakeResult) {
    if (!intake.selected_circuit_id) return;
    chooseCircuit(intake.selected_circuit_id, intake.fault_distance_ft);
    setTolerance(intake.tolerance_ft);
    setActiveWorkspace("operations");
  }

  function openGlobalSearch() {
    setActiveWorkspace("operations");
    window.setTimeout(() => searchInputRef.current?.focus(), 0);
  }

  function runCorrelation(event: FormEvent) {
    event.preventDefault();
    correlation.mutate({
      circuit_id: selectedCircuit,
      launch_asset_id: "pop-001",
      fault_distance_ft: faultDistance,
      tolerance_ft: tolerance,
    });
  }

  function generatePlan() {
    if (!correlation.data) return;
    fieldPlan.mutate({
      circuit_id: selectedCircuit,
      launch_asset_id: "pop-001",
      fault_distance_ft: faultDistance,
      tolerance_ft: tolerance,
      impact_asset_id: correlation.data.nearest_cable_segment.cable_id,
    });
  }

  if (overview.isError) {
    return (
      <main className="fatal-state">
        <XCircle />
        <h1>Photon-Ops API is unavailable</h1>
        <p>{overview.error.message}</p>
        <button onClick={() => overview.refetch()}>Retry connection</button>
      </main>
    );
  }

  return (
    <main className="ops-shell">
      <aside className="app-sidebar">
        <div className="workspace-lockup">
          <div className="brand-mark" aria-hidden="true"><span /><span /><span /></div>
          <div className="workspace-lockup-copy">
            <span>Workspace</span>
            <strong>Photon-Ops</strong>
          </div>
          <ChevronLeft className="workspace-collapse" size={15} aria-hidden="true" />
        </div>

        <nav className="workspace-switcher" aria-label="Primary workspace">
          <button className={activeWorkspace === "intake" ? "active" : ""} onClick={() => setActiveWorkspace("intake")}>
            <Sparkles size={17} />
            <span><strong>Navigator intake</strong><small>Guided investigation</small></span>
          </button>
          <button className={activeWorkspace === "operations" ? "active" : ""} onClick={() => setActiveWorkspace("operations")}>
            <MapIcon size={17} />
            <span><strong>Plant operations</strong><small>Satellite network map</small></span>
          </button>
          <button className={activeWorkspace === "bench" ? "active" : ""} onClick={() => setActiveWorkspace("bench")}>
            <Waves size={17} />
            <span><strong>Photon Bench</strong><small>Optical calculator</small></span>
          </button>
        </nav>

        <section className="sidebar-systems" aria-label="Connected systems">
          <p className="sidebar-label">Connected systems</p>
          <div className="system-line">
            <Database size={14} />
            <span><strong>{capabilities.data?.network_label ?? "Checking…"}</strong><small>Network record</small></span>
            <i className="live-dot" />
          </div>
          <div className="system-line">
            <Bot size={14} />
            <span><strong>{capabilities.data?.ai_enabled ? "AWS Bedrock" : "Deterministic demo"}</strong><small>Navigator mode</small></span>
            <i className={capabilities.data?.ai_enabled ? "live-dot" : "standby-dot"} />
          </div>
          <div className="sidebar-light-route" aria-hidden="true"><span /><i /><span /><i /><span /></div>
        </section>

        <div className="sidebar-footer">
          <div className="sidebar-region"><Radio size={15} /><span><small>Region</small><strong>Dexter, Maine</strong></span></div>
          {auth.mode === "entra" ? (
            <button className="identity-chip" onClick={auth.logout} title="Sign out">
              <UserRound size={15} /><span><small>Signed in</small><strong>{auth.displayName}</strong></span><LogOut size={13} />
            </button>
          ) : (
            <div className="identity-chip"><UserRound size={15} /><span><small>Session</small><strong>{auth.displayName}</strong></span></div>
          )}
        </div>
      </aside>

      <section className="app-main">
        <header className="ops-header">
          <div className="history-controls" aria-label="Browser history controls">
            <button onClick={() => window.history.back()} aria-label="Go back"><ArrowLeft size={16} /></button>
            <button onClick={() => window.history.forward()} aria-label="Go forward"><ArrowRight size={16} /></button>
          </div>
          <p className="topbar-path"><span>Photon-Ops</span><i>/</i><strong>{workspaceLabel}</strong></p>
          <div className="header-readout">
            <button className="command-search" onClick={openGlobalSearch}>
              <Search size={15} /><span>Search addresses, circuits, assets</span><kbd>⌘ K</kbd>
            </button>
            <div className="header-security"><ShieldCheck size={14} /><span>{auth.mode === "entra" ? "Entra protected" : "Demo session"}</span></div>
          </div>
        </header>

        {activeWorkspace === "intake" ? (
        <NavigatorIntake capabilities={capabilities.data} onOpenInvestigation={openNavigatorInvestigation} />
      ) : activeWorkspace === "operations" ? (
        <section className="workspace-grid">
        <aside className="left-rail panel-scroll">
          <section className="rail-section search-section">
            <label htmlFor="network-search" className="section-label">Find service or network object</label>
            <div className="search-box">
              <Search size={16} />
              <input
                ref={searchInputRef}
                id="network-search"
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="Address, circuit, or asset"
              />
              <kbd>⌘ K</kbd>
            </div>
            {searchQuery.length >= 2 && (
              <div className="search-results">
                {search.isLoading && <p>Tracing records…</p>}
                {search.data?.map((result) => (
                  <button key={`${result.result_type}-${result.id}`} onClick={() => chooseSearchResult(result)}>
                    <span><strong>{result.name}</strong><small>{result.subtitle}</small></span>
                    <ChevronRight size={14} />
                  </button>
                ))}
                {search.data?.length === 0 && <p>No mapped object matches that search.</p>}
              </div>
            )}
          </section>

          <section className="rail-section">
            <div className="section-heading"><span className="section-label">Map layers</span><MapIcon size={14} /></div>
            {[
              ["satellite", "Satellite · Esri World Imagery", "#9d7cff"],
              ["backbone", "Backbone fiber", "#2fc3e8"],
              ["distribution", "Distribution fiber", "#527e91"],
              ["drops", "Service drops", "#66889a"],
              ["assets", "Plant assets", "#f2a93b"],
            ].map(([key, label, color]) => (
              <label className="layer-toggle" key={key}>
                <input
                  type="checkbox"
                  checked={layers[key as keyof typeof layers]}
                  onChange={() => setLayers((current) => ({ ...current, [key]: !current[key as keyof typeof layers] }))}
                />
                <span className="layer-swatch" style={{ background: color }} />
                <span>{label}</span>
              </label>
            ))}
          </section>

          <section className="rail-section incidents-section">
            <div className="section-heading">
              <span className="section-label">Active incidents</span>
              <span className="count-chip">{overview.data?.incidents.length ?? 0}</span>
            </div>
            <div className="incident-list">
              {overview.data?.incidents.map((incident) => (
                <button
                  key={incident.id}
                  className={`incident-card ${incident.severity}`}
                  onClick={() => chooseIncident(incident)}
                >
                  <span className="severity-bar" />
                  <span className="incident-copy">
                    <small>{incident.severity} · {incident.status}</small>
                    <strong>{incident.title}</strong>
                    <span>{incident.circuit_id ?? incident.asset_id}</span>
                  </span>
                  <ChevronRight size={15} />
                </button>
              ))}
            </div>
          </section>

          <section className="rail-section circuits-section">
            <div className="section-heading"><span className="section-label">Service addresses</span><MapPin size={14} /></div>
            <div className="circuit-list">
              {overview.data?.circuits.map((circuit) => (
                <button
                  key={circuit.id}
                  className={circuit.id === selectedCircuit ? "selected" : ""}
                  onClick={() => chooseCircuit(circuit.id)}
                >
                  <span className="circuit-status" />
                  <span>
                    <strong>{circuit.service_address}</strong>
                    <small>
                      {circuit.service_lineage.account_type} · {circuit.service_lineage.lcp_code} / {circuit.service_lineage.splitter_id} / Port {String(circuit.service_lineage.splitter_port).padStart(2, "0")}
                    </small>
                    <em>{circuit.name}</em>
                  </span>
                </button>
              ))}
            </div>
          </section>
        </aside>

        <section className="map-stage">
          <div className="map-toolbar">
            <div>
              <p className="eyebrow">Address service path</p>
              <strong>{path.data?.service_address ?? "Loading service address…"}</strong>
              <span>
                {path.data
                  ? `${path.data.service_lineage.lcp_code} / ${path.data.service_lineage.splitter_id} / Port ${String(path.data.service_lineage.splitter_port).padStart(2, "0")} → premise · ${number.format(path.data.service_leg_length_ft)} ft · ${path.data.service_leg_segments.length} segments`
                  : "Resolving topology"}
              </span>
            </div>
            <div className="map-legend">
              <span><i className="legend-line route" />LCP → address</span>
              <span><i className="legend-dot fault" />OTDR event</span>
            </div>
          </div>
          <MapView overview={overview.data} path={path.data} correlation={correlation.data} layers={layers} />
          <div className="trace-ruler" aria-label="OTDR trace distance">
            <div className="ruler-heading"><Zap size={13} /><span>Optical route trace</span><strong>{number.format(faultDistance)} ft</strong></div>
            <div className="ruler-track">
              <span className="ruler-fill" style={{ width: `${Math.min(100, (faultDistance / (path.data?.total_length_ft || faultDistance)) * 100)}%` }} />
              <span className="ruler-cursor" style={{ left: `${Math.min(100, (faultDistance / (path.data?.total_length_ft || faultDistance)) * 100)}%` }} />
            </div>
            <div className="ruler-labels"><span>POP · 0</span><span>{path.data ? number.format(path.data.total_length_ft) : "—"} ft · subscriber</span></div>
          </div>
        </section>

        <aside className="right-rail panel-scroll">
          <section className="investigation-header">
            <p className="eyebrow">{path.data?.service_lineage.account_type ?? "Residential"} service investigation</p>
            <h2>{selectedCircuitSummary?.service_address ?? "Resolving service address…"}</h2>
            <p>{selectedCircuitSummary?.name ?? selectedCircuit} · {selectedCircuitSummary?.service_location_id}</p>
            <div className="status-row"><span><Activity size={13} />Active service</span><span>Strand {path.data?.segments.at(-1)?.strand_number ?? "—"}</span></div>
          </section>

          {path.data && (
            <section className="service-lineage-card">
              <MapPin size={17} />
              <div>
                <small>Serving LCP splitter port</small>
                <strong>{path.data.service_lineage.lcp_code} → {path.data.service_lineage.splitter_id} / Port {String(path.data.service_lineage.splitter_port).padStart(2, "0")}</strong>
                <span>{path.data.service_lineage.splitter_ratio} splitter · to {path.data.service_address}</span>
              </div>
            </section>
          )}

          <form className="analysis-form" onSubmit={runCorrelation}>
            <div className="section-heading"><span className="section-label">OTDR correlation</span><Crosshair size={15} /></div>
            <p className="helper">Distance is measured along the ordered circuit route—not as a straight line.</p>
            <label>
              <span>Launch point</span>
              <select value="pop-001" disabled><option>Dexter Central POP · pop-001</option></select>
            </label>
            <div className="form-row">
              <label><span>Fault distance</span><div className="unit-input"><input type="number" min="1" value={faultDistance} onChange={(event) => setFaultDistance(Number(event.target.value))} /><em>ft</em></div></label>
              <label><span>Tolerance</span><div className="unit-input"><input type="number" min="1" max="5000" value={tolerance} onChange={(event) => setTolerance(Number(event.target.value))} /><em>± ft</em></div></label>
            </div>
            <button className="primary-action" disabled={correlation.isPending || path.isLoading}>
              <LocateFixed size={16} />{correlation.isPending ? "Tracing route…" : "Correlate fault"}
            </button>
            {correlation.isError && <p className="inline-error">{correlation.error.message}</p>}
          </form>

          {correlation.data ? (
            <section className="result-section">
              <div className="result-flag"><span className={`confidence ${correlation.data.confidence}`}>{correlation.data.confidence} confidence</span><span>{number.format(correlation.data.offset_ft)} ft offset</span></div>
              <div className="fault-location">
                <span className="fault-icon"><Crosshair size={18} /></span>
                <div><small>Nearest mapped asset</small><strong>{correlation.data.nearest_asset.name}</strong><p>{correlation.data.nearest_cable_segment.cable_name}</p></div>
              </div>
              <p className="field-search"><AlertTriangle size={14} />{correlation.data.recommended_field_search_area.instruction}</p>
            </section>
          ) : (
            <section className="empty-investigation"><Crosshair /><strong>No route correlation yet</strong><p>Run the known 18,420 ft trace to locate the high-loss splice.</p></section>
          )}

          {impact.data && (
            <section className="impact-section">
              <div className="section-heading"><span className="section-label">Outage impact</span><Users size={15} /></div>
              <div className="impact-grid">
                <div><strong>{impact.data.affected_circuits.length}</strong><span>Circuits</span></div>
                <div><strong>{impact.data.business_accounts_affected}</strong><span>Business</span></div>
                <div><strong>{impact.data.residential_accounts_affected}</strong><span>Residential</span></div>
              </div>
              <p className="priority-readout"><AlertTriangle size={14} />{impact.data.suggested_restoration_priority}</p>
              {impact.data.available_alternate_paths.length > 0 && <p className="alternate-readout"><CheckCircle2 size={14} />Alternate path: {impact.data.available_alternate_paths.join(", ")}</p>}
            </section>
          )}

          <section className="plan-section">
            <div className="section-heading"><span className="section-label">Field action plan</span><ClipboardList size={15} /></div>
            <button className="secondary-action" onClick={generatePlan} disabled={!correlation.data || fieldPlan.isPending}>
              {fieldPlan.isPending ? "Building dispatch plan…" : "Generate field plan"}<ChevronRight size={15} />
            </button>
            {fieldPlan.data && (
              <article className="field-plan">
                <div><small>{fieldPlan.data.plan_id}</small><span>{fieldPlan.data.generated_by}</span></div>
                <h3>{fieldPlan.data.suspected_fault_location}</h3>
                {fieldPlan.data.executive_summary && <p>{fieldPlan.data.executive_summary}</p>}
                <dl>
                  <dt>Crew</dt><dd>{fieldPlan.data.recommended_crew_type}</dd>
                  <dt>Impact</dt><dd>{fieldPlan.data.affected_circuits_and_services}</dd>
                  <dt>First move</dt><dd>{fieldPlan.data.restoration_sequence[0]}</dd>
                </dl>
                <p className="assumption">{fieldPlan.data.confidence_and_assumptions}</p>
              </article>
            )}
          </section>
        </aside>
        </section>
      ) : (
        <PhotonBenchWorkspace
          circuits={overview.data?.circuits}
          path={path.data}
          selectedCircuit={selectedCircuit}
          onSelectCircuit={chooseCircuit}
        />
      )}
      </section>
    </main>
  );
}
