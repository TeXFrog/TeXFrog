import { ParseResult, TfOnlySpan, TfSourceBlock } from "./types";
import { resolveTagRanges } from "./tagResolver";

/**
 * Find the matching closing brace for an opening '{' at position pos.
 * Returns the index of the closing '}', or -1 if not found.
 * Handles nested braces and escaped characters.
 */
function findClosingBrace(text: string, openPos: number): number {
  let depth = 0;
  let i = openPos;
  while (i < text.length) {
    const ch = text[i];
    if (ch === "\\") {
      i += 2; // skip escaped character
      continue;
    }
    if (ch === "{") {
      depth++;
    } else if (ch === "}") {
      depth--;
      if (depth === 0) {
        return i;
      }
    }
    i++;
  }
  return -1;
}

/**
 * Convert a character offset in the document text to a 0-indexed line number.
 */
function offsetToLine(text: string, offset: number): number {
  let line = 0;
  for (let i = 0; i < offset && i < text.length; i++) {
    if (text[i] === "\n") {
      line++;
    }
  }
  return line;
}

/**
 * Extract the ordered game labels from \tfgames{...}.
 */
function extractGameLabels(text: string): string[] {
  const match = text.match(/\\tfgames\s*\{/);
  if (!match || match.index === undefined) {
    return [];
  }
  const openBrace = match.index + match[0].length - 1;
  const closeBrace = findClosingBrace(text, openBrace);
  if (closeBrace === -1) {
    return [];
  }
  const content = text.substring(openBrace + 1, closeBrace);
  return content
    .split(",")
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}

/**
 * Find all \begin{tfsource}{name} ... \end{tfsource} block ranges.
 */
function findSourceBlocks(text: string): TfSourceBlock[] {
  const blocks: TfSourceBlock[] = [];
  const beginRe = /\\begin\s*\{tfsource\}\s*\{[^}]*\}/g;
  const endRe = /\\end\s*\{tfsource\}/g;

  let beginMatch: RegExpExecArray | null;
  while ((beginMatch = beginRe.exec(text)) !== null) {
    // Find the next \end{tfsource} after this begin
    endRe.lastIndex = beginMatch.index + beginMatch[0].length;
    const endMatch = endRe.exec(text);
    if (endMatch) {
      blocks.push({
        startLine: offsetToLine(text, beginMatch.index),
        endLine: offsetToLine(text, endMatch.index + endMatch[0].length - 1),
      });
    }
  }
  return blocks;
}

/**
 * Find all \tfonly{tags}{content}, \tfonly*{tags}{content}, and
 * \tffigonly{content} spans within tfsource blocks.
 */
function findTfOnlySpans(
  text: string,
  sourceBlocks: TfSourceBlock[],
  orderedLabels: string[]
): TfOnlySpan[] {
  const spans: TfOnlySpan[] = [];

  // Build a set of character ranges that are inside tfsource blocks
  // We need to map line ranges back to character ranges for scanning
  const lines = text.split("\n");
  const lineOffsets: number[] = [];
  let offset = 0;
  for (const line of lines) {
    lineOffsets.push(offset);
    offset += line.length + 1; // +1 for the newline
  }

  for (const block of sourceBlocks) {
    const blockStart = lineOffsets[block.startLine];
    const blockEnd =
      block.endLine < lines.length
        ? lineOffsets[block.endLine] + lines[block.endLine].length
        : text.length;

    // Scan within this block for \tfonly, \tfonly*, \tffigonly
    let i = blockStart;
    while (i < blockEnd) {
      // Skip escaped backslashes
      if (text[i] === "\\" && i + 1 < blockEnd && text[i + 1] === "\\") {
        i += 2;
        continue;
      }

      // Check for \tffigonly
      if (text.startsWith("\\tffigonly", i)) {
        const cmdEnd = i + "\\tffigonly".length;
        // Skip whitespace
        let j = cmdEnd;
        while (j < blockEnd && (text[j] === " " || text[j] === "\t" || text[j] === "\n")) {
          j++;
        }
        if (j < blockEnd && text[j] === "{") {
          const closeBrace = findClosingBrace(text, j);
          if (closeBrace !== -1 && closeBrace <= blockEnd) {
            spans.push({
              startLine: offsetToLine(text, i),
              endLine: offsetToLine(text, closeBrace),
              tags: new Set<string>(),
              isFigOnly: true,
            });
            i = closeBrace + 1;
            continue;
          }
        }
      }

      // Check for \tfonly or \tfonly*
      if (text.startsWith("\\tfonly", i) && !text.startsWith("\\tffigonly", i)) {
        let cmdEnd = i + "\\tfonly".length;
        // Check for star variant
        if (cmdEnd < blockEnd && text[cmdEnd] === "*") {
          cmdEnd++;
        }
        // Skip whitespace
        let j = cmdEnd;
        while (j < blockEnd && (text[j] === " " || text[j] === "\t" || text[j] === "\n")) {
          j++;
        }
        // First brace group: tags
        if (j < blockEnd && text[j] === "{") {
          const tagsClose = findClosingBrace(text, j);
          if (tagsClose !== -1 && tagsClose < blockEnd) {
            const tagString = text.substring(j + 1, tagsClose);
            // Skip whitespace
            let k = tagsClose + 1;
            while (k < blockEnd && (text[k] === " " || text[k] === "\t" || text[k] === "\n")) {
              k++;
            }
            // Second brace group: content
            if (k < blockEnd && text[k] === "{") {
              const contentClose = findClosingBrace(text, k);
              if (contentClose !== -1 && contentClose <= blockEnd) {
                let resolvedTags: Set<string>;
                try {
                  resolvedTags = resolveTagRanges(tagString, orderedLabels);
                } catch {
                  resolvedTags = new Set<string>();
                }
                spans.push({
                  startLine: offsetToLine(text, i),
                  endLine: offsetToLine(text, contentClose),
                  tags: resolvedTags,
                  isFigOnly: false,
                });
                i = contentClose + 1;
                continue;
              }
            }
          }
        }
      }

      i++;
    }
  }

  return spans;
}

/**
 * Parse a .tex document for TeXFrog game definitions and conditional content spans.
 */
export function parseDocument(text: string): ParseResult {
  const orderedLabels = extractGameLabels(text);
  const sourceBlocks = findSourceBlocks(text);
  const spans = findTfOnlySpans(text, sourceBlocks, orderedLabels);

  return { orderedLabels, sourceBlocks, spans };
}
