// @vitest-environment jsdom
import { describe, it, expect, beforeEach } from "vitest";
import { readJSON, writeJSON, readString, writeString, removeKey } from "./storage";

describe("storage (localStorage wrapper)", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe("readJSON / writeJSON", () => {
    it("writes and reads back an object", () => {
      writeJSON("test-key", { name: "cartana", count: 3 });
      expect(readJSON("test-key", null)).toEqual({ name: "cartana", count: 3 });
    });

    it("returns fallback when key is missing", () => {
      expect(readJSON("missing", { default: true })).toEqual({ default: true });
    });

    it("returns fallback when stored value is invalid JSON", () => {
      localStorage.setItem("bad-json", "{not valid");
      expect(readJSON("bad-json", "fallback")).toBe("fallback");
    });

    it("writes arrays", () => {
      writeJSON("arr", [1, 2, 3]);
      expect(readJSON<number[]>("arr", [])).toEqual([1, 2, 3]);
    });
  });

  describe("readString / writeString", () => {
    it("writes and reads back a string", () => {
      writeString("key", "hello");
      expect(readString("key", "")).toBe("hello");
    });

    it("returns fallback when key is missing", () => {
      expect(readString("missing", "default")).toBe("default");
    });
  });

  describe("removeKey", () => {
    it("removes an existing key", () => {
      writeString("to-remove", "value");
      removeKey("to-remove");
      expect(readString("to-remove", "gone")).toBe("gone");
    });

    it("does not throw for missing key", () => {
      expect(() => removeKey("never-existed")).not.toThrow();
    });
  });
});
