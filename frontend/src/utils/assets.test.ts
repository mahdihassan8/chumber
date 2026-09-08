import { describe, expect, it } from "vitest";
import { formatSignedIQD } from "@/utils/assets";

describe("formatSignedIQD", () => {
  it("prefixes a positive amount with an explicit +", () => {
    expect(formatSignedIQD(300_000)).toBe("+300,000 IQD");
  });

  it("keeps the - sign on a negative amount", () => {
    expect(formatSignedIQD(-300_000)).toBe("-300,000 IQD");
  });

  it("shows no sign at all for exactly zero", () => {
    expect(formatSignedIQD(0)).toBe("0 IQD");
  });

  it("matches the spec's worked example in both directions", () => {
    // Total Inventory Value 1,000,000 - (Total User Money 600,000 + Chumber
    // Required 100,000) = +300,000, and the mirror-image negative case.
    expect(formatSignedIQD(1_000_000 - (600_000 + 100_000))).toBe("+300,000 IQD");
    expect(formatSignedIQD(600_000 + 100_000 - 1_000_000)).toBe("-300,000 IQD");
  });
});
