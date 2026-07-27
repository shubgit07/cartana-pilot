import { describe, it, expect } from "vitest";
import { AppError, NotFoundError, ValidationError, ConflictError, UnauthorizedError } from "./errors";

describe("AppError", () => {
  it("sets defaults", () => {
    const err = new AppError("boom");
    expect(err.message).toBe("boom");
    expect(err.status).toBe(500);
    expect(err.code).toBe("app_error");
    expect(err.name).toBe("AppError");
    expect(err.details).toBeUndefined();
  });

  it("accepts overrides", () => {
    const err = new AppError("bad", 422, "custom_code", { field: "name" });
    expect(err.status).toBe(422);
    expect(err.code).toBe("custom_code");
    expect(err.details).toEqual({ field: "name" });
  });

  it("is an Error instance", () => {
    expect(new AppError("x")).toBeInstanceOf(Error);
  });
});

describe("NotFoundError", () => {
  it("has 404 status", () => {
    const err = new NotFoundError();
    expect(err.status).toBe(404);
    expect(err.code).toBe("not_found");
    expect(err.message).toBe("Not found");
  });

  it("accepts custom message", () => {
    const err = new NotFoundError("Project 123 not found");
    expect(err.message).toBe("Project 123 not found");
  });

  it("is an AppError", () => {
    expect(new NotFoundError()).toBeInstanceOf(AppError);
  });
});

describe("ValidationError", () => {
  it("has 400 status", () => {
    expect(new ValidationError().status).toBe(400);
    expect(new ValidationError().code).toBe("validation_error");
  });
});

describe("ConflictError", () => {
  it("has 409 status", () => {
    expect(new ConflictError().status).toBe(409);
    expect(new ConflictError().code).toBe("conflict");
  });
});

describe("UnauthorizedError", () => {
  it("has 401 status", () => {
    expect(new UnauthorizedError().status).toBe(401);
    expect(new UnauthorizedError().code).toBe("unauthorized");
  });
});
