import * as vscode from "vscode";
import { parseDocument } from "./parser";
import { computeDimmedLines, dimmedLinesToRanges } from "./dimming";
import { ParseResult } from "./types";

/** Decoration type for dimmed (excluded) lines. */
const dimDecoration = vscode.window.createTextEditorDecorationType({
  opacity: "0.35",
});

/** Per-document state: selected game and cached parse result. */
const documentState = new Map<
  string,
  { selectedGame: string | null; parseResult: ParseResult }
>();

/** Status bar item showing the selected game. */
let statusBarItem: vscode.StatusBarItem;

/** Debounce timer for document change events. */
let debounceTimer: ReturnType<typeof setTimeout> | undefined;

function getState(uri: string): { selectedGame: string | null; parseResult: ParseResult } {
  let state = documentState.get(uri);
  if (!state) {
    state = {
      selectedGame: null,
      parseResult: { orderedLabels: [], sourceBlocks: [], spans: [] },
    };
    documentState.set(uri, state);
  }
  return state;
}

function updateDecorations(editor: vscode.TextEditor): void {
  const state = getState(editor.document.uri.toString());

  if (!state.selectedGame || state.parseResult.orderedLabels.length === 0) {
    editor.setDecorations(dimDecoration, []);
    return;
  }

  const dimmedLines = computeDimmedLines(
    state.parseResult,
    state.selectedGame,
    editor.document.lineCount
  );
  const ranges = dimmedLinesToRanges(dimmedLines, editor.document);
  editor.setDecorations(dimDecoration, ranges);
}

function reparseAndUpdate(editor: vscode.TextEditor): void {
  const state = getState(editor.document.uri.toString());
  state.parseResult = parseDocument(editor.document.getText());

  // If the selected game no longer exists, clear it
  if (
    state.selectedGame &&
    !state.parseResult.orderedLabels.includes(state.selectedGame)
  ) {
    state.selectedGame = null;
  }

  updateDecorations(editor);
  updateStatusBar(editor);
}

function updateStatusBar(editor: vscode.TextEditor): void {
  const state = getState(editor.document.uri.toString());

  if (state.parseResult.orderedLabels.length === 0) {
    statusBarItem.hide();
    return;
  }

  if (state.selectedGame) {
    statusBarItem.text = `$(telescope) ${state.selectedGame}`;
    statusBarItem.tooltip = `TeXFrog: viewing game ${state.selectedGame}. Click to change.`;
  } else {
    statusBarItem.text = "$(telescope) TeXFrog";
    statusBarItem.tooltip = "TeXFrog: no game selected. Click to select.";
  }
  statusBarItem.show();
}

async function selectGame(): Promise<void> {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    return;
  }

  const state = getState(editor.document.uri.toString());

  if (state.parseResult.orderedLabels.length === 0) {
    // Try parsing first in case it hasn't been parsed yet
    state.parseResult = parseDocument(editor.document.getText());
  }

  if (state.parseResult.orderedLabels.length === 0) {
    vscode.window.showInformationMessage(
      "No TeXFrog games found in this file."
    );
    return;
  }

  const items: vscode.QuickPickItem[] = state.parseResult.orderedLabels.map(
    (label) => ({
      label,
      description: state.selectedGame === label ? "(current)" : undefined,
    })
  );

  items.push({ label: "", kind: vscode.QuickPickItemKind.Separator });
  items.push({
    label: "Clear Selection",
    description: "Remove game dimming",
  });

  const pick = await vscode.window.showQuickPick(items, {
    placeHolder: "Select a game to highlight",
  });

  if (!pick) {
    return; // cancelled
  }

  if (pick.label === "Clear Selection") {
    state.selectedGame = null;
  } else {
    state.selectedGame = pick.label;
  }

  updateDecorations(editor);
  updateStatusBar(editor);
}

function clearGame(): void {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    return;
  }

  const state = getState(editor.document.uri.toString());
  state.selectedGame = null;
  updateDecorations(editor);
  updateStatusBar(editor);
}

export function activate(context: vscode.ExtensionContext): void {
  // Status bar
  statusBarItem = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Left,
    100
  );
  statusBarItem.command = "texfrog.selectGame";
  context.subscriptions.push(statusBarItem);

  // Commands
  context.subscriptions.push(
    vscode.commands.registerCommand("texfrog.selectGame", selectGame)
  );
  context.subscriptions.push(
    vscode.commands.registerCommand("texfrog.clearGame", clearGame)
  );

  // Parse the active editor on activation
  if (vscode.window.activeTextEditor) {
    reparseAndUpdate(vscode.window.activeTextEditor);
  }

  // Re-parse and update when switching editors
  context.subscriptions.push(
    vscode.window.onDidChangeActiveTextEditor((editor) => {
      if (editor) {
        reparseAndUpdate(editor);
      } else {
        statusBarItem.hide();
      }
    })
  );

  // Debounced re-parse on document change
  context.subscriptions.push(
    vscode.workspace.onDidChangeTextDocument((event) => {
      const editor = vscode.window.activeTextEditor;
      if (editor && event.document === editor.document) {
        if (debounceTimer) {
          clearTimeout(debounceTimer);
        }
        debounceTimer = setTimeout(() => {
          reparseAndUpdate(editor);
        }, 300);
      }
    })
  );

  // Clean up state when documents close
  context.subscriptions.push(
    vscode.workspace.onDidCloseTextDocument((document) => {
      documentState.delete(document.uri.toString());
    })
  );
}

export function deactivate(): void {
  if (debounceTimer) {
    clearTimeout(debounceTimer);
  }
  documentState.clear();
}
