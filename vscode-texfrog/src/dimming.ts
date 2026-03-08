import * as vscode from "vscode";
import { ParseResult } from "./types";

/**
 * Compute the set of 0-indexed line numbers that should be dimmed
 * for the given selected game.
 */
export function computeDimmedLines(
  parseResult: ParseResult,
  selectedGame: string,
  totalLines: number
): Set<number> {
  const { sourceBlocks, spans } = parseResult;
  const dimmed = new Set<number>();

  // Build set of lines inside tfsource blocks
  const inSource = new Set<number>();
  for (const block of sourceBlocks) {
    for (let line = block.startLine; line <= block.endLine; line++) {
      inSource.add(line);
    }
  }

  // For each line in a tfsource block, check if it's covered by any span
  // that includes the selected game. If covered only by excluding spans, dim it.
  for (let line = 0; line < totalLines; line++) {
    if (!inSource.has(line)) {
      continue; // outside tfsource — never dimmed
    }

    // Find all spans that cover this line
    const coveringSpans = spans.filter(
      (s) => line >= s.startLine && line <= s.endLine
    );

    if (coveringSpans.length === 0) {
      continue; // common content — not dimmed
    }

    // Line is visible if ANY covering span includes the game
    const visible = coveringSpans.some(
      (s) => !s.isFigOnly && s.tags.has(selectedGame)
    );

    if (!visible) {
      dimmed.add(line);
    }
  }

  return dimmed;
}

/**
 * Convert a set of dimmed line numbers into an array of VS Code Ranges,
 * merging adjacent lines into contiguous ranges.
 */
export function dimmedLinesToRanges(
  dimmedLines: Set<number>,
  document: vscode.TextDocument
): vscode.Range[] {
  if (dimmedLines.size === 0) {
    return [];
  }

  const sorted = Array.from(dimmedLines).sort((a, b) => a - b);
  const ranges: vscode.Range[] = [];
  let rangeStart = sorted[0];
  let rangeEnd = sorted[0];

  for (let i = 1; i < sorted.length; i++) {
    if (sorted[i] === rangeEnd + 1) {
      rangeEnd = sorted[i];
    } else {
      ranges.push(
        new vscode.Range(
          document.lineAt(rangeStart).range.start,
          document.lineAt(rangeEnd).range.end
        )
      );
      rangeStart = sorted[i];
      rangeEnd = sorted[i];
    }
  }

  // Push the last range
  ranges.push(
    new vscode.Range(
      document.lineAt(rangeStart).range.start,
      document.lineAt(rangeEnd).range.end
    )
  );

  return ranges;
}
