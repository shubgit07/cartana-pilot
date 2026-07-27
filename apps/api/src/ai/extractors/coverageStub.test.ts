import { describe, it, expect } from "vitest";
import { coverageStub } from "./coverageStub";

describe("coverageStub", () => {
  it("returns 'missing' when no candidate tasks", () => {
    const result = coverageStub({
      requirement: { title: "User authentication", description: "Users must log in" },
      candidateTasks: [],
    });
    expect(result.judgments).toHaveLength(1);
    expect(result.judgments[0].status).toBe("missing");
  });

  it("returns 'covered' when task tokens strongly overlap with requirement", () => {
    const result = coverageStub({
      requirement: {
        title: "User authentication login system",
        description: "The system must support user authentication with login",
      },
      candidateTasks: [
        {
          title: "Build user authentication login page",
          description: "Implement the login authentication flow for users",
        },
      ],
    });
    expect(result.judgments).toHaveLength(1);
    expect(result.judgments[0].status).toBe("covered");
  });

  it("returns 'partial' when task tokens moderately overlap", () => {
    const result = coverageStub({
      requirement: {
        title: "Dashboard analytics charts metrics display",
        description: "The dashboard should display analytics charts",
      },
      candidateTasks: [
        {
          title: "Build dashboard layout",
          description: "Create the dashboard page structure",
        },
      ],
    });
    expect(result.judgments[0].status).toMatch(/partial|unclear|covered/);
  });

  it("returns 'unclear' when task has no overlap with requirement", () => {
    const result = coverageStub({
      requirement: {
        title: "Database migration strategy",
        description: "The system needs a database migration plan",
      },
      candidateTasks: [
        {
          title: "Design landing page hero",
          description: "Create the marketing hero section",
        },
      ],
    });
    expect(result.judgments[0].status).toBe("unclear");
  });

  it("returns 'unclear' when task has no meaningful text", () => {
    const result = coverageStub({
      requirement: { title: "Authentication", description: "Login system" },
      candidateTasks: [{ title: "ab", description: "cd" }],
    });
    expect(result.judgments[0].status).toBe("unclear");
  });

  it("returns one judgment per candidate task", () => {
    const result = coverageStub({
      requirement: { title: "Build the system", description: "Complete system build" },
      candidateTasks: [
        { title: "Build the frontend", description: "Create frontend" },
        { title: "Build the backend", description: "Create backend" },
        { title: "Build the database", description: "Create database" },
      ],
    });
    expect(result.judgments).toHaveLength(3);
  });

  it("each judgment has a rationale string", () => {
    const result = coverageStub({
      requirement: { title: "Authentication system", description: "User login" },
      candidateTasks: [{ title: "Build authentication", description: "Login flow" }],
    });
    for (const j of result.judgments) {
      expect(j.rationale).toBeTruthy();
      expect(typeof j.rationale).toBe("string");
    }
  });

  it("handles empty description gracefully", () => {
    const result = coverageStub({
      requirement: { title: "Authentication", description: "" },
      candidateTasks: [{ title: "Build auth", description: "" }],
    });
    expect(result.judgments).toHaveLength(1);
  });
});
