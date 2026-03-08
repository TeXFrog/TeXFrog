/** A span of lines covered by a \tfonly, \tfonly*, or \tffigonly command. */
export interface TfOnlySpan {
  /** Document line where the \tfonly command starts (0-indexed). */
  startLine: number;
  /** Document line where the closing brace ends (0-indexed). */
  endLine: number;
  /** Resolved set of game labels that include this content. Empty for \tffigonly. */
  tags: Set<string>;
  /** True if this is a \tffigonly block (always dimmed for individual games). */
  isFigOnly: boolean;
}

/** A tfsource block's line range. */
export interface TfSourceBlock {
  /** Line of \begin{tfsource}{name} (0-indexed). */
  startLine: number;
  /** Line of \end{tfsource} (0-indexed). */
  endLine: number;
}

/** Result of parsing a .tex document for TeXFrog content. */
export interface ParseResult {
  /** Ordered game/reduction labels from \tfgames{...}. */
  orderedLabels: string[];
  /** tfsource block ranges. */
  sourceBlocks: TfSourceBlock[];
  /** All \tfonly / \tfonly* / \tffigonly spans within tfsource blocks. */
  spans: TfOnlySpan[];
}
