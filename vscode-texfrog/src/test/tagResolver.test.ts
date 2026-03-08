import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { resolveTagRanges } from "../tagResolver";

const LABELS = ["G0", "G1", "Red1", "G2", "G3"];

describe("resolveTagRanges", () => {
  it("resolves a single label", () => {
    const result = resolveTagRanges("G0", LABELS);
    assert.deepStrictEqual(result, new Set(["G0"]));
  });

  it("resolves comma-separated labels", () => {
    const result = resolveTagRanges("G0, G2", LABELS);
    assert.deepStrictEqual(result, new Set(["G0", "G2"]));
  });

  it("resolves a range", () => {
    const result = resolveTagRanges("G0-G2", LABELS);
    // G0 (pos 0), G1 (pos 1), Red1 (pos 2), G2 (pos 3)
    assert.deepStrictEqual(result, new Set(["G0", "G1", "Red1", "G2"]));
  });

  it("resolves mixed labels and ranges", () => {
    const result = resolveTagRanges("G0, G2-G3", LABELS);
    assert.deepStrictEqual(result, new Set(["G0", "G2", "G3"]));
  });

  it("handles whitespace around tokens", () => {
    const result = resolveTagRanges("  G0 , G1  ", LABELS);
    assert.deepStrictEqual(result, new Set(["G0", "G1"]));
  });

  it("handles empty string", () => {
    const result = resolveTagRanges("", LABELS);
    assert.deepStrictEqual(result, new Set());
  });

  it("treats unknown labels as literals", () => {
    const result = resolveTagRanges("Unknown", LABELS);
    assert.deepStrictEqual(result, new Set(["Unknown"]));
  });

  it("throws on reversed range", () => {
    assert.throws(
      () => resolveTagRanges("G2-G0", LABELS),
      /reversed/
    );
  });

  it("resolves single-element range", () => {
    const result = resolveTagRanges("G1-G1", LABELS);
    assert.deepStrictEqual(result, new Set(["G1"]));
  });

  it("handles label containing hyphen as literal when not a valid range", () => {
    const labels = ["my-label", "G0", "G1"];
    const result = resolveTagRanges("my-label", labels);
    assert.ok(result.has("my-label"));
  });
});
