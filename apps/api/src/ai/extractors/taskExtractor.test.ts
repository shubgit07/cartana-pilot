import { describe, it, expect } from "vitest";
import { extractTasksStub } from "./taskExtractor";

const makeChunks = (texts: string[]) =>
  texts.map((text, i) => ({ id: `c${i}`, position: i, text }));

const reqs = [
  { title: "User Authentication", description: "Users must log in with email and password." },
  { title: "Dashboard Analytics", description: "The dashboard should display charts and metrics." },
];

describe("extractTasksStub", () => {
  it("returns empty array when no chunks", () => {
    expect(
      extractTasksStub({ sourceFilename: "f.txt", chunks: [], requirements: [] })
    ).toEqual([]);
  });

  it("extracts sentences starting with action verbs", () => {
    const result = extractTasksStub({
      sourceFilename: "f.txt",
      chunks: makeChunks(["Build the login page with email and password fields."]),
      requirements: [],
    });
    expect(result).toHaveLength(1);
    expect(result[0].title).toContain("Build");
    expect(result[0].chunkIds).toEqual(["c0"]);
  });

  it("capitalizes the leading verb", () => {
    const result = extractTasksStub({
      sourceFilename: "f.txt",
      chunks: makeChunks(["create the database schema for users."]),
      requirements: [],
    });
    expect(result[0].title.startsWith("Create")).toBe(true);
  });

  it("detects multiple action verbs", () => {
    const verbs = ["build", "create", "implement", "design", "develop", "test", "deploy", "configure", "write", "integrate"];
    for (const verb of verbs) {
      const result = extractTasksStub({
        sourceFilename: "f.txt",
        chunks: makeChunks([`${verb} the component for the project.`]),
        requirements: [],
      });
      expect(result, `verb "${verb}"`).toHaveLength(1);
    }
  });

  it("ignores sentences without a leading action verb", () => {
    const result = extractTasksStub({
      sourceFilename: "f.txt",
      chunks: makeChunks(["The weather is nice today. Let's go for a walk."]),
      requirements: [],
    });
    expect(result).toEqual([]);
  });

  it("deduplicates by title (case-insensitive)", () => {
    const result = extractTasksStub({
      sourceFilename: "f.txt",
      chunks: makeChunks([
        "Build the login page.",
        "Build the login page.",
      ]),
      requirements: [],
    });
    expect(result).toHaveLength(1);
  });

  it("links task to best-matching requirement by token overlap", () => {
    const result = extractTasksStub({
      sourceFilename: "f.txt",
      chunks: makeChunks(["Build the user authentication login flow."]),
      requirements: reqs,
    });
    expect(result).toHaveLength(1);
    expect(result[0].linkedRequirementTitle).toBe("User Authentication");
  });

  it("returns no link when no requirements overlap", () => {
    const result = extractTasksStub({
      sourceFilename: "f.txt",
      chunks: makeChunks(["Deploy the server to production."]),
      requirements: reqs,
    });
    expect(result).toHaveLength(1);
    expect(result[0].linkedRequirementTitle).toBeUndefined();
  });

  it("returns no link when requirements array is empty", () => {
    const result = extractTasksStub({
      sourceFilename: "f.txt",
      chunks: makeChunks(["Build the login page."]),
      requirements: [],
    });
    expect(result[0].linkedRequirementTitle).toBeUndefined();
  });

  it("caps at 60 results", () => {
    const chunks = Array.from({ length: 70 }, (_, i) => ({
      id: `c${i}`,
      position: i,
      text: `Build feature number ${i} for the system.`,
    }));
    const result = extractTasksStub({
      sourceFilename: "f.txt",
      chunks,
      requirements: [],
    });
    expect(result.length).toBeLessThanOrEqual(60);
  });

  it("truncates long titles at 160 chars + ellipsis", () => {
    const long = "build " + "word ".repeat(40) + "end.";
    const result = extractTasksStub({
      sourceFilename: "f.txt",
      chunks: makeChunks([long]),
      requirements: [],
    });
    if (result.length > 0) {
      expect(result[0].title.length).toBeLessThanOrEqual(161);
    }
  });
});
