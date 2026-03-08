# TeXFrog for VS Code

[TeXFrog](https://texfrog.github.io/) helps cryptographers manage game-hopping proofs in LaTeX. You write your pseudocode once in a single `.tex` file and tag content with `\tfonly{tags}{content}` to indicate which games each line belongs to. TeXFrog can then produce per-game renderings, comparison figures, and an interactive HTML proof viewer — all from that one source file.

This extension brings TeXFrog awareness into VS Code, letting you visualize individual games directly in your editor.

## Features

### Game selection with dimming

Select a game from your proof and the extension dims lines that don't belong to that game, making it easy to see what each game looks like without leaving your editor.

Use the command **TeXFrog: Select Game** to pick a game from a quick-pick menu. Lines excluded from the selected game are dimmed to 35% opacity. Documents with multiple proofs (multiple `tfsource` blocks) are grouped by source in the picker.

### Status bar indicator

When a `.tex` file contains TeXFrog games, a status bar item appears showing the currently selected game (or "TeXFrog" if no game is selected). Click it to open the game picker.

### Live updates

The extension re-parses your document as you type (with a 300ms debounce) and updates the dimming automatically. If you delete a game that was selected, the selection is cleared.

## Commands

| Command | Keybinding | Description |
|---------|------------|-------------|
| **TeXFrog: Select Game** | `Cmd+K Cmd+G` (macOS) / `Ctrl+K Ctrl+G` | Open the game picker |
| **TeXFrog: Clear Game Selection** | — | Remove dimming and clear the selected game |

## Installation

### From a `.vsix` file

If you received a `.vsix` file:

- **VS Code UI:** Extensions view → `···` menu → *Install from VSIX...*
- **Command line:** `code --install-extension texfrog-0.0.1.vsix`

### From source

```bash
cd vscode-texfrog
npm install
npm run compile
```

Then use **Developer: Install Extension from Location...** in VS Code and select the `vscode-texfrog` directory, or press `F5` to launch a development Extension Host.

## Requirements

No external dependencies. The extension activates automatically when a LaTeX file is opened and parses `\tfonly`, `\tfgames`, and `tfsource` commands directly from the source text.

## Learn more

- [TeXFrog documentation](https://texfrog.github.io/)
- [GitHub repository](https://github.com/TeXFrog/TeXFrog)
- [Writing a proof](https://github.com/TeXFrog/TeXFrog/blob/main/docs/writing-proofs.md)

## License

Apache License 2.0. See [LICENSE.txt](https://github.com/TeXFrog/TeXFrog/blob/main/LICENSE.txt) for details.
