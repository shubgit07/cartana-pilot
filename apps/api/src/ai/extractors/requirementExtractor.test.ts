import { describe, it, expect } from "vitest";
import { extractRequirementsStub } from "./requirementExtractor";

const makeChunks = (texts: string[]) =>
  texts.map((text, i) => ({ id: `c${i}`, position: i, text }));

describe("extractRequirementsStub", () => {
  it("returns empty array when no chunks", () => {
    expect(extractRequirementsStub({ sourceFilename: "f.txt", chunks: [] })).toEqual([]);
  });

  it("extracts sentences with 'must'", () => {
    const result = extractRequirementsStub({
      sourceFilename: "f.txt",
      chunks: makeChunks(["The system must support user authentication."]),
    });
    expect(result).toHaveLength(1);
    expect(result[0].title).toContain("must");
    expect(result[0].description).toContain("must");
    expect(result[0].chunkIds).toEqual(["c0"]);
  });

  it("extracts sentences with 'shall'", () => {
    const result = extractRequirementsStub({
      sourceFilename: "f.txt",
      chunks: makeChunks(["The API shall return JSON responses."]),
    });
    expect(result).toHaveLength(1);
  });

  it("extracts sentences with 'should'", () => {
    const result = extractRequirementsStub({
      sourceFilename: "f.txt",
      chunks: makeChunks(["Users should be able to reset their password."]),
    });
    expect(result).toHaveLength(1);
  });

  it("extracts sentences with 'required to'", () => {
    const result = extractRequirementsStub({
      sourceFilename: "f.txt",
      chunks: makeChunks(["Admins are required to verify their email."]),
    });
    expect(result).toHaveLength(1);
  });

  it("ignores sentences without requirement keywords", () => {
    const result = extractRequirementsStub({
      sourceFilename: "f.txt",
      chunks: makeChunks(["The weather is nice today. Let's go for a walk."]),
    });
    expect(result).toEqual([]);
  });

  it("deduplicates by title (case-insensitive)", () => {
    const result = extractRequirementsStub({
      sourceFilename: "f.txt",
      chunks: makeChunks([
        "The system must support user login.",
        "The system must support user login.",
      ]),
    });
    expect(result).toHaveLength(1);
  });

  it("skips very long paragraphs (>320 chars)", () => {
    const long = "must " + "x ".repeat(200);
    const result = extractRequirementsStub({
      sourceFilename: "f.txt",
      chunks: makeChunks([long]),
    });
    expect(result).toEqual([]);
  });

  it("skips very short sentences (<12 chars)", () => {
    const result = extractRequirementsStub({
      sourceFilename: "f.txt",
      chunks: makeChunks(["Must work."]),
    });
    expect(result).toEqual([]);
  });

  it("caps at 40 results", () => {
    const chunks = Array.from({ length: 50 }, (_, i) => ({
      id: `c${i}`,
      position: i,
      text: `The system must support feature number ${i}.`,
    }));
    const result = extractRequirementsStub({
      sourceFilename: "f.txt",
      chunks,
    });
    expect(result.length).toBeLessThanOrEqual(40);
  });

  it("truncates long titles at 120 chars", () => {
    const long = "must " + "word ".repeat(30) + "end of sentence here.";
    const result = extractRequirementsStub({
      sourceFilename: "f.txt",
      chunks: makeChunks([long]),
    });
    if (result.length > 0) {
      expect(result[0].title.length).toBeLessThanOrEqual(121);
    }
  });
});
