import { describe, expect, it } from "vitest";

import { calculateOpticalBudget, feetToKilometers } from "./optics";

describe("Photon Bench optical budget", () => {
  it("converts mapped route feet to kilometers", () => {
    expect(feetToKilometers(3280.83989501312)).toBeCloseTo(1, 12);
    expect(feetToKilometers(18420)).toBeCloseTo(5.614416, 6);
  });

  it("calculates a passing OS2 circuit from route and event loss", () => {
    const budget = calculateOpticalBudget({
      lengthFt: 18420,
      fiberType: "os2",
      wavelengthNm: 1550,
      profile: "typical",
      connectors: 2,
      fusionSplices: 4,
      mechanicalSplices: 0,
      splitterRatio: "none",
      txPowerDbm: -3,
      rxSensitivityDbm: -18,
      rxOverloadDbm: -1,
      engineeringMarginDb: 3,
    });

    expect(budget.fiberLossDb).toBeCloseTo(1.6843248, 6);
    expect(budget.totalLossDb).toBeCloseTo(2.8843248, 6);
    expect(budget.predictedRxDbm).toBeCloseTo(-5.8843248, 6);
    expect(budget.headroomDb).toBeCloseTo(9.1156752, 6);
    expect(budget.status).toBe("pass");
  });

  it("fails a link when splitter loss consumes the usable budget", () => {
    const budget = calculateOpticalBudget({
      lengthFt: 60000,
      fiberType: "os2",
      wavelengthNm: 1550,
      profile: "tia",
      connectors: 4,
      fusionSplices: 8,
      mechanicalSplices: 0,
      splitterRatio: "1:64",
      txPowerDbm: 2,
      rxSensitivityDbm: -28,
      rxOverloadDbm: -8,
      engineeringMarginDb: 3,
    });

    expect(budget.headroomDb).toBeLessThan(0);
    expect(budget.status).toBe("fail");
  });

  it("resolves an incompatible wavelength when switching from OS2 to OM4", () => {
    const budget = calculateOpticalBudget({
      lengthFt: 3280.83989501312,
      fiberType: "om4",
      wavelengthNm: 1550,
      profile: "typical",
      connectors: 0,
      fusionSplices: 0,
      mechanicalSplices: 0,
      splitterRatio: "none",
      txPowerDbm: -3,
      rxSensitivityDbm: -18,
      rxOverloadDbm: -1,
      engineeringMarginDb: 3,
    });

    expect(budget.wavelengthNm).toBe(850);
    expect(budget.attenuationDbPerKm).toBe(3);
    expect(budget.fiberLossDb).toBeCloseTo(3, 12);
  });
});
