import { describe, it, expect } from "vitest";
import { formatDate, formatDateTime, formatCount, formatScore } from "./format";

describe("formatDate", () => {
  it("formats a valid ISO date string", () => {
    const result = formatDate("2026-01-15T10:00:00Z");
    expect(result).toMatch(/Jan 15, 2026/);
  });

  it("formats a Date object", () => {
    const result = formatDate(new Date("2026-06-01T00:00:00Z"));
    expect(result).toMatch(/2026/);
  });

  it("returns empty string for invalid date", () => {
    expect(formatDate("not-a-date")).toBe("");
    expect(formatDate(new Date("invalid"))).toBe("");
  });

  it("returns empty string for null-ish input", () => {
    expect(formatDate(null as unknown as string)).toBe("");
  });
});

describe("formatDateTime", () => {
  it("formats a valid ISO date-time string", () => {
    const result = formatDateTime("2026-01-15T14:30:00Z");
    expect(result).toMatch(/Jan 15, 2026/);
    expect(result.length).toBeGreaterThan(10);
  });

  it("returns empty string for invalid date", () => {
    expect(formatDateTime("bad")).toBe("");
  });
});

describe("formatCount", () => {
  it("uses singular form when count is 1", () => {
    expect(formatCount(1, "source")).toBe("1 source");
  });

  it("uses plural form when count is not 1", () => {
    expect(formatCount(0, "source")).toBe("0 sources");
    expect(formatCount(2, "source")).toBe("2 sources");
    expect(formatCount(100, "source")).toBe("100 sources");
  });

  it("uses custom plural when provided", () => {
    expect(formatCount(2, "child", "children")).toBe("2 children");
  });

  it("formats large numbers with locale separators", () => {
    expect(formatCount(1000, "item")).toBe("1,000 items");
  });
});

describe("formatScore", () => {
  it("formats to 2 decimal places", () => {
    expect(formatScore(0.123456)).toBe("0.12");
    expect(formatScore(0.9)).toBe("0.90");
    expect(formatScore(1)).toBe("1.00");
  });

  it("handles edge values", () => {
    expect(formatScore(0)).toBe("0.00");
    expect(formatScore(0.999)).toBe("1.00");
  });
});
