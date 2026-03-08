import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { parseDocument } from "../parser";

describe("extractGameLabels", () => {
  it("extracts labels from \\tfgames{source}{games}", () => {
    const text = "\\tfgames{indcpa}{G0, G1, Red1, G2, G3}";
    const result = parseDocument(text);
    assert.deepStrictEqual(result.orderedLabels, [
      "G0",
      "G1",
      "Red1",
      "G2",
      "G3",
    ]);
    assert.deepStrictEqual(result.labelsBySource, [
      { source: "indcpa", labels: ["G0", "G1", "Red1", "G2", "G3"] },
    ]);
  });

  it("skips source name and parses second brace group", () => {
    const text = "\\tfgames{mysource}{A, B}";
    const result = parseDocument(text);
    assert.deepStrictEqual(result.orderedLabels, ["A", "B"]);
    // Should NOT include "mysource"
    assert.ok(!result.orderedLabels.includes("mysource"));
    assert.strictEqual(result.labelsBySource[0].source, "mysource");
  });

  it("handles whitespace between brace groups", () => {
    const text = "\\tfgames{src}  \n  {X, Y, Z}";
    const result = parseDocument(text);
    assert.deepStrictEqual(result.orderedLabels, ["X", "Y", "Z"]);
  });

  it("collects labels from multiple \\tfgames calls", () => {
    const text =
      "\\tfgames{proof1}{G0, G1}\n\\tfgames{proof2}{A0, A1, A2}";
    const result = parseDocument(text);
    assert.deepStrictEqual(result.orderedLabels, [
      "G0",
      "G1",
      "A0",
      "A1",
      "A2",
    ]);
    assert.deepStrictEqual(result.labelsBySource, [
      { source: "proof1", labels: ["G0", "G1"] },
      { source: "proof2", labels: ["A0", "A1", "A2"] },
    ]);
  });

  it("returns empty array when no \\tfgames present", () => {
    const text = "\\documentclass{article}\n\\begin{document}Hello\\end{document}";
    const result = parseDocument(text);
    assert.deepStrictEqual(result.orderedLabels, []);
    assert.deepStrictEqual(result.labelsBySource, []);
  });

  it("handles nested braces in source name", () => {
    const text = "\\tfgames{my{nested}source}{G0, G1}";
    const result = parseDocument(text);
    assert.deepStrictEqual(result.orderedLabels, ["G0", "G1"]);
    assert.strictEqual(result.labelsBySource[0].source, "my{nested}source");
  });

  it("skips \\tfgames with missing second brace group", () => {
    const text = "\\tfgames{onlyonegroup}";
    const result = parseDocument(text);
    assert.deepStrictEqual(result.orderedLabels, []);
    assert.deepStrictEqual(result.labelsBySource, []);
  });
});

describe("findSourceBlocks", () => {
  it("finds a single tfsource block", () => {
    const text =
      "preamble\n\\begin{tfsource}{test}\nbody line 1\nbody line 2\n\\end{tfsource}\npostamble";
    const result = parseDocument(text);
    assert.strictEqual(result.sourceBlocks.length, 1);
    assert.strictEqual(result.sourceBlocks[0].startLine, 1);
    assert.strictEqual(result.sourceBlocks[0].endLine, 4);
  });

  it("finds multiple tfsource blocks", () => {
    const text =
      "\\begin{tfsource}{a}\nfoo\n\\end{tfsource}\n" +
      "\\begin{tfsource}{b}\nbar\n\\end{tfsource}";
    const result = parseDocument(text);
    assert.strictEqual(result.sourceBlocks.length, 2);
    assert.strictEqual(result.sourceBlocks[0].startLine, 0);
    assert.strictEqual(result.sourceBlocks[1].startLine, 3);
  });

  it("returns empty when no tfsource blocks", () => {
    const text = "no source blocks here";
    const result = parseDocument(text);
    assert.strictEqual(result.sourceBlocks.length, 0);
  });
});

describe("findTfOnlySpans", () => {
  it("finds \\tfonly spans inside tfsource", () => {
    const text =
      "\\tfgames{test}{G0, G1}\n" +
      "\\begin{tfsource}{test}\n" +
      "\\tfonly{G0}{content for G0}\n" +
      "\\end{tfsource}";
    const result = parseDocument(text);
    assert.strictEqual(result.spans.length, 1);
    assert.ok(result.spans[0].tags.has("G0"));
    assert.ok(!result.spans[0].isFigOnly);
  });

  it("finds \\tfonly* spans", () => {
    const text =
      "\\tfgames{test}{G0, G1}\n" +
      "\\begin{tfsource}{test}\n" +
      "\\tfonly*{G0}{starred content}\n" +
      "\\end{tfsource}";
    const result = parseDocument(text);
    assert.strictEqual(result.spans.length, 1);
    assert.ok(result.spans[0].tags.has("G0"));
  });

  it("finds \\tffigonly spans", () => {
    const text =
      "\\tfgames{test}{G0, G1}\n" +
      "\\begin{tfsource}{test}\n" +
      "\\tffigonly{figure content}\n" +
      "\\end{tfsource}";
    const result = parseDocument(text);
    assert.strictEqual(result.spans.length, 1);
    assert.ok(result.spans[0].isFigOnly);
    assert.strictEqual(result.spans[0].tags.size, 0);
  });

  it("ignores \\tfonly outside tfsource blocks", () => {
    const text =
      "\\tfgames{test}{G0, G1}\n" +
      "\\tfonly{G0}{outside source block}";
    const result = parseDocument(text);
    assert.strictEqual(result.spans.length, 0);
  });

  it("resolves range tags like G0-G2", () => {
    const text =
      "\\tfgames{test}{G0, G1, G2, G3}\n" +
      "\\begin{tfsource}{test}\n" +
      "\\tfonly{G0-G2}{range content}\n" +
      "\\end{tfsource}";
    const result = parseDocument(text);
    assert.strictEqual(result.spans.length, 1);
    assert.ok(result.spans[0].tags.has("G0"));
    assert.ok(result.spans[0].tags.has("G1"));
    assert.ok(result.spans[0].tags.has("G2"));
    assert.ok(!result.spans[0].tags.has("G3"));
  });

  it("handles multiple spans on consecutive lines", () => {
    const text =
      "\\tfgames{test}{G0, G1}\n" +
      "\\begin{tfsource}{test}\n" +
      "\\tfonly{G0}{line for G0}\n" +
      "\\tfonly{G1}{line for G1}\n" +
      "\\end{tfsource}";
    const result = parseDocument(text);
    assert.strictEqual(result.spans.length, 2);
  });
});

describe("parseDocument integration", () => {
  it("parses a realistic document", () => {
    const text = [
      "\\documentclass{article}",
      "\\usepackage[package=cryptocode]{texfrog}",
      "\\tfgames{indcpa}{G0, G1, Red1, G2}",
      "",
      "\\begin{tfsource}{indcpa}",
      "\\begin{pchstack}[boxed]",
      "  \\procedure{Game}{",
      "    \\tfonly{G0}{x \\gets 0 \\\\}",
      "    \\tfonly{G1,G2}{x \\gets 1 \\\\}",
      "    \\tfonly{Red1}{x \\gets \\mathcal{O}(0) \\\\}",
      "    \\pcreturn x",
      "  }",
      "\\end{pchstack}",
      "\\end{tfsource}",
    ].join("\n");

    const result = parseDocument(text);
    assert.deepStrictEqual(result.orderedLabels, [
      "G0",
      "G1",
      "Red1",
      "G2",
    ]);
    assert.strictEqual(result.sourceBlocks.length, 1);
    assert.strictEqual(result.sourceBlocks[0].startLine, 4);
    assert.strictEqual(result.sourceBlocks[0].endLine, 13);
    assert.strictEqual(result.spans.length, 3);
  });
});
