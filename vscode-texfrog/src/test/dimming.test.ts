import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { computeDimmedLines } from "../dimming";
import { ParseResult } from "../types";

function makeParseResult(overrides: Partial<ParseResult> = {}): ParseResult {
  return {
    orderedLabels: [],
    sourceBlocks: [],
    spans: [],
    ...overrides,
  };
}

describe("computeDimmedLines", () => {
  it("returns empty set when no source blocks", () => {
    const result = computeDimmedLines(makeParseResult(), "G0", 10);
    assert.strictEqual(result.size, 0);
  });

  it("does not dim lines outside tfsource blocks", () => {
    const pr = makeParseResult({
      sourceBlocks: [{ startLine: 5, endLine: 10 }],
      spans: [
        { startLine: 7, endLine: 7, tags: new Set(["G1"]), isFigOnly: false },
      ],
    });
    const result = computeDimmedLines(pr, "G0", 15);
    // Lines 0-4, 11-14 should NOT be dimmed (outside source block)
    assert.ok(!result.has(0));
    assert.ok(!result.has(4));
    assert.ok(!result.has(11));
  });

  it("does not dim common content lines (no spans)", () => {
    const pr = makeParseResult({
      sourceBlocks: [{ startLine: 0, endLine: 5 }],
    });
    const result = computeDimmedLines(pr, "G0", 6);
    assert.strictEqual(result.size, 0);
  });

  it("dims lines covered by spans that exclude selected game", () => {
    const pr = makeParseResult({
      sourceBlocks: [{ startLine: 0, endLine: 5 }],
      spans: [
        { startLine: 2, endLine: 2, tags: new Set(["G1"]), isFigOnly: false },
      ],
    });
    const result = computeDimmedLines(pr, "G0", 6);
    assert.ok(result.has(2));
  });

  it("does not dim lines covered by spans that include selected game", () => {
    const pr = makeParseResult({
      sourceBlocks: [{ startLine: 0, endLine: 5 }],
      spans: [
        { startLine: 2, endLine: 2, tags: new Set(["G0"]), isFigOnly: false },
      ],
    });
    const result = computeDimmedLines(pr, "G0", 6);
    assert.ok(!result.has(2));
  });

  it("dims tffigonly lines for any game", () => {
    const pr = makeParseResult({
      sourceBlocks: [{ startLine: 0, endLine: 5 }],
      spans: [
        { startLine: 3, endLine: 3, tags: new Set(), isFigOnly: true },
      ],
    });
    const result = computeDimmedLines(pr, "G0", 6);
    assert.ok(result.has(3));
  });

  it("line visible if any covering span includes game", () => {
    const pr = makeParseResult({
      sourceBlocks: [{ startLine: 0, endLine: 5 }],
      spans: [
        { startLine: 2, endLine: 2, tags: new Set(["G1"]), isFigOnly: false },
        { startLine: 2, endLine: 2, tags: new Set(["G0"]), isFigOnly: false },
      ],
    });
    const result = computeDimmedLines(pr, "G0", 6);
    // G0 is in one of the spans, so not dimmed
    assert.ok(!result.has(2));
  });

  it("handles multi-line spans", () => {
    const pr = makeParseResult({
      sourceBlocks: [{ startLine: 0, endLine: 10 }],
      spans: [
        { startLine: 3, endLine: 5, tags: new Set(["G1"]), isFigOnly: false },
      ],
    });
    const result = computeDimmedLines(pr, "G0", 11);
    assert.ok(result.has(3));
    assert.ok(result.has(4));
    assert.ok(result.has(5));
    assert.ok(!result.has(2));
    assert.ok(!result.has(6));
  });
});
