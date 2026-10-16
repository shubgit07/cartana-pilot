import { describe, it, expect } from "vitest";
import { NAVIGATION_TABS } from "./constants";

describe("NAVIGATION_TABS", () => {
  it("contains the expected tabs in order", () => {
    expect(NAVIGATION_TABS).toEqual([
      "requirements",
      "repository",
      "compliance",
    ]);
  });

  it("is a readonly tuple (as const)", () => {
    expect(NAVIGATION_TABS.length).toBe(3);
    expect(NAVIGATION_TABS[0]).toBe("requirements");
  });
});
