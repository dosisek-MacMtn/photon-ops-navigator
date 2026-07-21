export type FiberType = "os2" | "om4";
export type AllowanceProfile = "typical" | "tia";
export type LinkStatus = "pass" | "review" | "fail";

export const FEET_PER_KILOMETER = 3280.83989501312;

export const FIBER_DEFINITIONS = {
  os2: {
    label: "OS2 · outside-plant single-mode",
    wavelengths: [1270, 1310, 1490, 1550, 1577],
  },
  om4: {
    label: "OM4 · laser-optimized multimode",
    wavelengths: [850, 1300],
  },
} as const;

const ATTENUATION: Record<AllowanceProfile, Record<FiberType, Record<number, number>>> = {
  typical: {
    os2: { 1270: 0.4, 1310: 0.4, 1490: 0.3, 1550: 0.3, 1577: 0.3 },
    om4: { 850: 3.0, 1300: 1.0 },
  },
  tia: {
    os2: { 1270: 0.5, 1310: 0.5, 1490: 0.5, 1550: 0.5, 1577: 0.5 },
    om4: { 850: 3.5, 1300: 1.5 },
  },
};

const EVENT_ALLOWANCES: Record<AllowanceProfile, { connectorDb: number; fusionDb: number; mechanicalDb: number }> = {
  typical: { connectorDb: 0.3, fusionDb: 0.15, mechanicalDb: 0.3 },
  tia: { connectorDb: 0.75, fusionDb: 0.3, mechanicalDb: 0.3 },
};

export const SPLITTER_LOSS = {
  none: 0,
  "1:2": 3.6,
  "1:4": 6.8,
  "1:8": 10,
  "1:16": 13,
  "1:32": 16,
  "1:64": 19.5,
} as const;

export type SplitterRatio = keyof typeof SPLITTER_LOSS;

export type OpticalBudgetInput = {
  lengthFt: number;
  fiberType: FiberType;
  wavelengthNm: number;
  profile: AllowanceProfile;
  connectors: number;
  fusionSplices: number;
  mechanicalSplices: number;
  splitterRatio: SplitterRatio;
  txPowerDbm: number;
  rxSensitivityDbm: number;
  rxOverloadDbm: number;
  engineeringMarginDb: number;
};

export type OpticalBudget = {
  wavelengthNm: number;
  lengthKm: number;
  attenuationDbPerKm: number;
  fiberLossDb: number;
  connectorLossDb: number;
  fusionLossDb: number;
  mechanicalLossDb: number;
  splitterLossDb: number;
  totalLossDb: number;
  equipmentBudgetDb: number;
  usableBudgetDb: number;
  predictedRxDbm: number;
  headroomDb: number;
  status: LinkStatus;
};

export function feetToKilometers(feet: number): number {
  return finiteNonnegative(feet) / FEET_PER_KILOMETER;
}

export function attenuationFor(
  profile: AllowanceProfile,
  fiberType: FiberType,
  wavelengthNm: number,
): number {
  const attenuation = ATTENUATION[profile]?.[fiberType]?.[wavelengthNm];
  if (attenuation === undefined) {
    throw new Error(`No ${profile} attenuation allowance for ${fiberType} at ${wavelengthNm} nm.`);
  }
  return attenuation;
}

export function resolveWavelength(fiberType: FiberType, requestedWavelengthNm: number): number {
  const wavelengths = FIBER_DEFINITIONS[fiberType].wavelengths as readonly number[];
  return wavelengths.includes(requestedWavelengthNm) ? requestedWavelengthNm : wavelengths[0];
}

export function calculateOpticalBudget(input: OpticalBudgetInput): OpticalBudget {
  const lengthKm = feetToKilometers(input.lengthFt);
  const wavelengthNm = resolveWavelength(input.fiberType, input.wavelengthNm);
  const attenuationDbPerKm = attenuationFor(input.profile, input.fiberType, wavelengthNm);
  const allowances = EVENT_ALLOWANCES[input.profile];
  const fiberLossDb = lengthKm * attenuationDbPerKm;
  const connectorLossDb = integerCount(input.connectors) * allowances.connectorDb;
  const fusionLossDb = integerCount(input.fusionSplices) * allowances.fusionDb;
  const mechanicalLossDb = integerCount(input.mechanicalSplices) * allowances.mechanicalDb;
  const splitterLossDb = SPLITTER_LOSS[input.splitterRatio] ?? 0;
  const totalLossDb =
    fiberLossDb + connectorLossDb + fusionLossDb + mechanicalLossDb + splitterLossDb;
  const equipmentBudgetDb = finiteNumber(input.txPowerDbm) - finiteNumber(input.rxSensitivityDbm);
  const usableBudgetDb = equipmentBudgetDb - finiteNonnegative(input.engineeringMarginDb);
  const predictedRxDbm = finiteNumber(input.txPowerDbm) - totalLossDb;
  const headroomDb = usableBudgetDb - totalLossDb;
  const overloaded = predictedRxDbm > finiteNumber(input.rxOverloadDbm);
  const status: LinkStatus =
    headroomDb < 0 || predictedRxDbm < input.rxSensitivityDbm || overloaded
      ? "fail"
      : headroomDb < 2
        ? "review"
        : "pass";

  return {
    wavelengthNm,
    lengthKm,
    attenuationDbPerKm,
    fiberLossDb,
    connectorLossDb,
    fusionLossDb,
    mechanicalLossDb,
    splitterLossDb,
    totalLossDb,
    equipmentBudgetDb,
    usableBudgetDb,
    predictedRxDbm,
    headroomDb,
    status,
  };
}

function integerCount(value: number): number {
  return Math.max(0, Math.floor(finiteNumber(value)));
}

function finiteNonnegative(value: number): number {
  return Math.max(0, finiteNumber(value));
}

function finiteNumber(value: number): number {
  return Number.isFinite(value) ? value : 0;
}
