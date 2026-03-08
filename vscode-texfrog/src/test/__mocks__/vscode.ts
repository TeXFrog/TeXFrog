// Minimal vscode mock for unit testing modules that import vscode.
// Only stubs used by dimming.ts are needed.

export class Range {
  constructor(
    public start: Position,
    public end: Position
  ) {}
}

export class Position {
  constructor(
    public line: number,
    public character: number
  ) {}
}
