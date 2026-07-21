"use client";

import { Activity, Cable, CircleGauge, Gauge, RadioTower, Ruler, Waves } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  FIBER_DEFINITIONS,
  SPLITTER_LOSS,
  calculateOpticalBudget,
  resolveWavelength,
  type AllowanceProfile,
  type FiberType,
  type SplitterRatio,
} from "@/lib/optics";
import type { CircuitPath, CircuitSummary } from "@/types/network";

type Props = {
  circuits?: CircuitSummary[];
  path?: CircuitPath;
  selectedCircuit: string;
  onSelectCircuit: (circuitId: string) => void;
};

const whole = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
const decimal = new Intl.NumberFormat("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function PhotonBenchWorkspace({ circuits, path, selectedCircuit, onSelectCircuit }: Props) {
  const [fiberType, setFiberType] = useState<FiberType>("os2");
  const [wavelengthNm, setWavelengthNm] = useState(1550);
  const [profile, setProfile] = useState<AllowanceProfile>("typical");
  const [connectors, setConnectors] = useState(2);
  const [fusionSplices, setFusionSplices] = useState(4);
  const [mechanicalSplices, setMechanicalSplices] = useState(0);
  const [splitterRatio, setSplitterRatio] = useState<SplitterRatio>("none");
  const [txPowerDbm, setTxPowerDbm] = useState(-3);
  const [rxSensitivityDbm, setRxSensitivityDbm] = useState(-18);
  const [engineeringMarginDb, setEngineeringMarginDb] = useState(3);
  const [measuredLoss, setMeasuredLoss] = useState("");

  const derivedSplices = useMemo(() => {
    if (!path) return 0;
    const closures = new Set(
      path.service_leg_segments
        .map((segment) => segment.end_asset_name)
        .filter((name) => name.toLowerCase().includes("closure")),
    );
    return closures.size;
  }, [path]);

  useEffect(() => {
    setFusionSplices(derivedSplices);
    setMeasuredLoss("");
  }, [derivedSplices, selectedCircuit]);

  useEffect(() => {
    const compatibleWavelength = resolveWavelength(fiberType, wavelengthNm);
    if (compatibleWavelength !== wavelengthNm) setWavelengthNm(compatibleWavelength);
  }, [fiberType, wavelengthNm]);

  useEffect(() => {
    const servingRatio = path?.service_lineage.splitter_ratio;
    if (servingRatio && servingRatio in SPLITTER_LOSS) {
      setSplitterRatio(servingRatio as SplitterRatio);
      if (servingRatio !== "none") {
        setTxPowerDbm(3);
        setRxSensitivityDbm(-28);
      }
    }
  }, [path?.service_lineage.splitter_ratio]);

  const budget = useMemo(
    () =>
      calculateOpticalBudget({
        lengthFt: path?.service_leg_length_ft ?? 0,
        fiberType,
        wavelengthNm,
        profile,
        connectors,
        fusionSplices,
        mechanicalSplices,
        splitterRatio,
        txPowerDbm,
        rxSensitivityDbm,
        rxOverloadDbm: -1,
        engineeringMarginDb,
      }),
    [
      connectors,
      engineeringMarginDb,
      fiberType,
      fusionSplices,
      mechanicalSplices,
      path?.service_leg_length_ft,
      profile,
      rxSensitivityDbm,
      splitterRatio,
      txPowerDbm,
      wavelengthNm,
    ],
  );

  const measured = measuredLoss === "" ? null : Number(measuredLoss);
  const measuredDelta = measured === null || !Number.isFinite(measured) ? null : measured - budget.totalLossDb;
  const lossRail = Math.min(100, Math.max(0, (budget.totalLossDb / Math.max(0.1, budget.usableBudgetDb)) * 100));

  return (
    <section className="bench-workspace">
      <aside className="bench-controls panel-scroll">
        <div className="bench-section bench-intro">
          <p className="eyebrow">Address optical model</p>
          <h2>Photon Bench</h2>
          <p>Turn mapped plant distance into a planning-grade optical loss budget.</p>
        </div>

        <div className="bench-section">
          <label className="bench-field">
            <span>Service address</span>
            <select value={selectedCircuit} onChange={(event) => onSelectCircuit(event.target.value)}>
              {circuits?.map((circuit) => (
                <option key={circuit.id} value={circuit.id}>{circuit.service_address} · {circuit.name}</option>
              ))}
            </select>
          </label>
          <div className="bench-route-readout">
            <Ruler size={16} />
            <span>
              <strong>{whole.format(path?.service_leg_length_ft ?? 0)} ft</strong>
              <small>{path ? `${path.service_lineage.lcp_code} / ${path.service_lineage.splitter_id} / Port ${String(path.service_lineage.splitter_port).padStart(2, "0")}` : "Resolving serving path"}</small>
            </span>
          </div>
        </div>

        <div className="bench-section">
          <div className="section-heading"><span className="section-label">Fiber and source</span><Waves size={15} /></div>
          <div className="bench-segmented">
            {(["os2", "om4"] as FiberType[]).map((type) => (
              <button
                key={type}
                className={fiberType === type ? "active" : ""}
                onClick={() => {
                  setFiberType(type);
                  setWavelengthNm(resolveWavelength(type, wavelengthNm));
                }}
              >
                {type.toUpperCase()}
              </button>
            ))}
          </div>
          <label className="bench-field">
            <span>Wavelength</span>
            <select value={wavelengthNm} onChange={(event) => setWavelengthNm(Number(event.target.value))}>
              {FIBER_DEFINITIONS[fiberType].wavelengths.map((wavelength) => (
                <option key={wavelength} value={wavelength}>{wavelength} nm</option>
              ))}
            </select>
          </label>
          <label className="bench-field">
            <span>Allowance profile</span>
            <select value={profile} onChange={(event) => setProfile(event.target.value as AllowanceProfile)}>
              <option value="typical">FOA typical planning</option>
              <option value="tia">ANSI/TIA maximum</option>
            </select>
          </label>
          <p className="bench-note">{FIBER_DEFINITIONS[fiberType].label} · {budget.attenuationDbPerKm.toFixed(2)} dB/km</p>
        </div>

        <div className="bench-section">
          <div className="section-heading"><span className="section-label">Passive events</span><Cable size={15} /></div>
          <div className="bench-input-grid">
            <NumberField label="Connectors" value={connectors} onChange={setConnectors} min={0} step={1} />
            <NumberField label="Fusion splices" value={fusionSplices} onChange={setFusionSplices} min={0} step={1} />
            <NumberField label="Mechanical" value={mechanicalSplices} onChange={setMechanicalSplices} min={0} step={1} />
            <label className="bench-field compact">
              <span>Splitter</span>
              <select value={splitterRatio} onChange={(event) => setSplitterRatio(event.target.value as SplitterRatio)}>
                {Object.keys(SPLITTER_LOSS).map((ratio) => (
                  <option key={ratio} value={ratio}>{ratio === "none" ? "None" : ratio}</option>
                ))}
              </select>
            </label>
          </div>
        </div>

        <div className="bench-section">
          <div className="section-heading"><span className="section-label">Equipment window · replace with actuals</span><RadioTower size={15} /></div>
          <div className="bench-input-grid">
            <NumberField label="Tx power · dBm" value={txPowerDbm} onChange={setTxPowerDbm} step={0.5} />
            <NumberField label="Rx sensitivity" value={rxSensitivityDbm} onChange={setRxSensitivityDbm} step={0.5} />
            <NumberField label="Margin · dB" value={engineeringMarginDb} onChange={setEngineeringMarginDb} min={0} step={0.5} />
            <label className="bench-field compact">
              <span>Measured loss · dB</span>
              <input type="number" min="0" step="0.01" value={measuredLoss} placeholder="Optional" onChange={(event) => setMeasuredLoss(event.target.value)} />
            </label>
          </div>
        </div>
      </aside>

      <section className="bench-stage panel-scroll">
        <div className="bench-stage-header">
          <div><p className="eyebrow">LCP splitter port → address</p><h2>{path?.service_address ?? "Loading service address…"}</h2><span>{path ? `${path.circuit_name} · ${path.service_lineage.lcp_code} / ${path.service_lineage.splitter_id} / Port ${String(path.service_lineage.splitter_port).padStart(2, "0")}` : "Resolving serving path"}</span></div>
          <span className={`bench-verdict ${budget.status}`}>{budget.status}</span>
        </div>

        <div className="photon-route" aria-label="Animated optical path visualization">
          <div className="route-meta"><span>TX · {txPowerDbm.toFixed(1)} dBm</span><span>{path?.service_leg_segments.length ?? 0} LCP-to-address segments</span><span>RX · {budget.predictedRxDbm.toFixed(1)} dBm</span></div>
          <svg viewBox="0 0 820 180" role="img" aria-label="Photon pulse travelling across the selected circuit">
            <defs>
              <linearGradient id="route-energy" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0" stopColor="#9d7cff" />
                <stop offset="0.55" stopColor="#2fc3e8" />
                <stop offset="1" stopColor="#58d69b" />
              </linearGradient>
              <filter id="route-glow"><feGaussianBlur stdDeviation="5" result="blur" /><feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
            </defs>
            <path className="route-shadow" d="M40 92 C150 22 230 162 340 92 S540 22 640 92 S745 150 780 92" />
            <path className="route-energy" d="M40 92 C150 22 230 162 340 92 S540 22 640 92 S745 150 780 92" />
            {(path?.service_leg_segments ?? []).map((segment, index, all) => {
              const x = 40 + (index / Math.max(1, all.length - 1)) * 740;
              return <circle key={segment.cable_id} className="route-node" cx={x} cy="92" r="4" />;
            })}
            <circle className="photon-pulse" cx="40" cy="92" r="7" filter="url(#route-glow)" />
          </svg>
          <p>Photon Bench uses accumulated cable distance from the network model—not straight-line map distance.</p>
        </div>

        <div className="loss-rail-card">
          <div className="loss-rail-heading"><span>Calculated plant loss</span><strong>{budget.totalLossDb.toFixed(2)} dB</strong></div>
          <div className="loss-rail"><span style={{ width: `${lossRail}%` }} /><i style={{ left: `${lossRail}%` }} /></div>
          <div className="loss-rail-scale"><span>0 dB</span><span>Usable budget · {budget.usableBudgetDb.toFixed(1)} dB</span></div>
        </div>

        <div className="bench-ledger">
          <div className="section-heading"><span className="section-label">Loss ledger</span><Activity size={15} /></div>
          <div className="ledger-row"><span>Fiber · {decimal.format(budget.lengthKm)} km × {budget.attenuationDbPerKm.toFixed(2)}</span><strong>{budget.fiberLossDb.toFixed(2)} dB</strong></div>
          <div className="ledger-row"><span>Connections · {connectors}</span><strong>{budget.connectorLossDb.toFixed(2)} dB</strong></div>
          <div className="ledger-row"><span>Fusion splices · {fusionSplices}</span><strong>{budget.fusionLossDb.toFixed(2)} dB</strong></div>
          <div className="ledger-row"><span>Mechanical splices · {mechanicalSplices}</span><strong>{budget.mechanicalLossDb.toFixed(2)} dB</strong></div>
          <div className="ledger-row"><span>Splitter · {splitterRatio === "none" ? "none" : splitterRatio}</span><strong>{budget.splitterLossDb.toFixed(2)} dB</strong></div>
          <div className="ledger-row total"><span>Total modeled loss</span><strong>{budget.totalLossDb.toFixed(2)} dB</strong></div>
        </div>

        <div className="segment-ledger">
          <div className="section-heading"><span className="section-label">Mapped segment contribution</span><CircleGauge size={15} /></div>
          <div className="segment-table">
            {path?.service_leg_segments.map((segment) => (
              <div className="segment-row" key={`${segment.sequence}-${segment.cable_id}`}>
                <span className="segment-index">{String(segment.sequence).padStart(2, "0")}</span>
                <span><strong>{segment.cable_name}</strong><small>{segment.start_asset_name} → {segment.end_asset_name}</small></span>
                <span>{whole.format(segment.length_ft)} ft</span>
                <strong>{(segment.length_ft / 3280.83989501312 * budget.attenuationDbPerKm).toFixed(2)} dB</strong>
              </div>
            ))}
          </div>
        </div>
      </section>

      <aside className="bench-results panel-scroll">
        <div className={`budget-orbit ${budget.status}`}>
          <div><span>Design headroom</span><strong>{budget.headroomDb.toFixed(2)}</strong><small>dB after margin</small></div>
        </div>

        <div className="bench-metrics">
          <Metric icon={<Gauge size={16} />} label="Equipment budget" value={`${budget.equipmentBudgetDb.toFixed(1)} dB`} />
          <Metric icon={<CircleGauge size={16} />} label="Engineering margin" value={`${engineeringMarginDb.toFixed(1)} dB`} />
          <Metric icon={<RadioTower size={16} />} label="Predicted receive" value={`${budget.predictedRxDbm.toFixed(2)} dBm`} />
        </div>

        <div className="bench-result-copy">
          <p className="eyebrow">Engineering readout</p>
          <h3>{budget.status === "pass" ? "Route has usable optical margin." : budget.status === "review" ? "Route is near the planning limit." : "Route exceeds the planning window."}</h3>
          <p>
            The selected {profile === "typical" ? "FOA typical" : "ANSI/TIA maximum"} allowances predict {budget.totalLossDb.toFixed(2)} dB of plant loss at {budget.wavelengthNm} nm.
          </p>
        </div>

        {measuredDelta !== null && (
          <div className={`measured-card ${Math.abs(measuredDelta) > 1 ? "review" : "pass"}`}>
            <span>OTDR comparison</span>
            <strong>{measuredDelta >= 0 ? "+" : ""}{measuredDelta.toFixed(2)} dB</strong>
            <p>Measured loss is {Math.abs(measuredDelta).toFixed(2)} dB {measuredDelta >= 0 ? "above" : "below"} the model.</p>
          </div>
        )}

        <div className="bench-disclaimer">
          <strong>Planning aid</strong>
          <p>Confirm project specifications, manufacturer limits, calibrated OLTS results, and bidirectional OTDR traces before acceptance or dispatch.</p>
        </div>
      </aside>
    </section>
  );
}

function NumberField({
  label,
  value,
  onChange,
  min,
  step,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min?: number;
  step: number;
}) {
  return (
    <label className="bench-field compact">
      <span>{label}</span>
      <input type="number" value={value} min={min} step={step} onChange={(event) => onChange(Number(event.target.value))} />
    </label>
  );
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return <div className="bench-metric"><span>{icon}{label}</span><strong>{value}</strong></div>;
}
