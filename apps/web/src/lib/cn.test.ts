import { describe, it, expect } from "vitest";
import { cn } from "./cn";

describe("cn", () => {
  it("joins string classes", () => {
    expect(cn("foo", "bar")).toBe("foo bar");
  });

  it("handles conditional classes", () => {
    expect(cn("base", false && "no", true && "yes")).toBe("base yes");
  });

  it("handles undefined and null", () => {
    expect(cn("base", undefined, null, "end")).toBe("base end");
  });

  it("deduplicates conflicting tailwind classes (tailwind-merge)", () => {
    expect(cn("px-2", "px-4")).toBe("px-4");
    expect(cn("text-sm", "text-lg")).toBe("text-lg");
  });

  it("preserves non-conflicting classes", () => {
    expect(cn("px-2 py-1", "text-center")).toBe("px-2 py-1 text-center");
  });

  it("handles empty input", () => {
    expect(cn()).toBe("");
  });

  it("handles arrays", () => {
    expect(cn(["foo", "bar"], "baz")).toBe("foo bar baz");
  });

  it("handles objects (clsx syntax)", () => {
    expect(cn({ active: true, disabled: false })).toBe("active");
  });
});
