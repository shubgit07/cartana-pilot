import { describe, it, expect } from "vitest";
import { dedupeKey } from "./dedupe";

describe("dedupeKey", () => {
  it("produces a deterministic hex string", () => {
    const key = dedupeKey("src-1", "User Login");
    expect(key).toMatch(/^[0-9a-f]{64}$/);
  });

  it("is stable for identical inputs", () => {
    expect(dedupeKey("src-1", "User Login")).toBe(dedupeKey("src-1", "User Login"));
  });

  it("changes when sourceId changes", () => {
    expect(dedupeKey("src-1", "User Login")).not.toBe(dedupeKey("src-2", "User Login"));
  });

  it("normalizes whitespace in title", () => {
    expect(dedupeKey("src-1", "User   Login")).toBe(dedupeKey("src-1", "User Login"));
    expect(dedupeKey("src-1", " User Login ")).toBe(dedupeKey("src-1", "User Login"));
  });

  it("normalizes case in title", () => {
    expect(dedupeKey("src-1", "USER LOGIN")).toBe(dedupeKey("src-1", "user login"));
  });

  it("treats empty title deterministically", () => {
    expect(dedupeKey("src-1", "")).toBe(dedupeKey("src-1", "   "));
  });
});
