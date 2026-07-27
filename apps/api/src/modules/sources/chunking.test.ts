import { describe, it, expect } from "vitest";
import { chunkText } from "./chunking";

describe("chunkText", () => {
  it("returns empty array for empty input", () => {
    expect(chunkText("")).toEqual([]);
    expect(chunkText("   \n\n  ")).toEqual([]);
  });

  it("returns single chunk for short text", () => {
    const result = chunkText("Hello world this is a short text.");
    expect(result).toHaveLength(1);
    expect(result[0].position).toBe(0);
    expect(result[0].text).toContain("Hello world");
  });

  it("splits long text into multiple chunks", () => {
    const long = "A".repeat(2000);
    const result = chunkText(long);
    expect(result.length).toBeGreaterThan(1);
    for (let i = 0; i < result.length; i++) {
      expect(result[i].position).toBe(i);
    }
  });

  it("respects maximum chunk size (~700 chars)", () => {
    const long = "word ".repeat(500);
    const result = chunkText(long);
    for (const chunk of result) {
      expect(chunk.text.length).toBeLessThanOrEqual(800);
    }
  });

  it("produces overlap between consecutive chunks", () => {
    const text = Array.from({ length: 50 }, (_, i) => `Sentence ${i}. This is a test sentence with enough words.`).join(" ");
    const result = chunkText(text);
    if (result.length < 2) return;
    const tail = result[0].text.slice(-50);
    expect(result[1].text).toContain(tail.slice(-20));
  });

  it("normalizes CRLF to LF", () => {
    const result = chunkText("Line one\r\nLine two\r\n");
    expect(result[0].text).not.toContain("\r");
  });

  it("trims whitespace from chunks", () => {
    const result = chunkText("  Hello world.  ");
    expect(result[0].text).toBe("Hello world.");
  });
});
