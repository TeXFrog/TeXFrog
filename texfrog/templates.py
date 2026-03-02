"""Inline templates for ``texfrog init``."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# cryptocode templates
# ---------------------------------------------------------------------------

CRYPTOCODE_YAML = r"""# TeXFrog proof configuration
#
# Edit this file to describe your game-hopping proof.
# Run `texfrog latex proof.yaml` to generate LaTeX output.
# Run `texfrog html build proof.yaml` to generate an interactive HTML viewer.

# LaTeX macro files to \input (relative to this file).
# .sty/.cls files are copied but loaded via \usepackage instead of \input.
macros:
  - macros.tex

# Combined source file containing all game pseudocode (relative to this file).
source: games_source.tex

# Package profile: "cryptocode" (default) or "nicodemus".
# package: cryptocode

# Games and reductions, listed in proof order.
# Tag ranges like G0-G2 are resolved by POSITION in this list.
# IMPORTANT: the order here determines what ranges like G0-G1 mean.
games:
  - label: G0
    latex_name: 'G_0'
    description: 'The starting game.'

  - label: G1
    latex_name: 'G_1'
    description: 'Replace the real value with a random one.'

  # Reductions sit between the games they bridge.
  # 'reduction: true' displays them separately in the HTML viewer.
  # 'related_games' shows clean copies of those games alongside the reduction.
  - label: Red1
    latex_name: '\Bdversary'
    description: 'Reduction bridging \tfgamename{G0} and \tfgamename{G1}.'
    reduction: true
    related_games: [G0, G1]

  - label: G2
    latex_name: 'G_2'
    description: 'The final game, where the adversary has no advantage.'

# Per-game commentary shown in the HTML viewer and LaTeX harness.
commentary:
  G0: |
    The starting game.
  G1: |
    Games \tfgamename{G0} and \tfgamename{G1} differ in how $y$ is computed.
  Red1: |
    Reduction \tfgamename{Red1} queries an external oracle instead of
    computing $f(k)$ directly.
  G2: |
    The final game.

# Consolidated figures showing multiple games side by side.
figures:
  - label: all_games
    games: "G0,G1,G2,Red1"
"""

CRYPTOCODE_SOURCE = r"""% TeXFrog combined source file.
%
% Tag syntax (at end of line):  %:tags: label1,label2-label3
%   - Lines with no %:tags: comment appear in EVERY game.
%   - Lines tagged with labels appear only in those games.
%   - Ranges like G0-G1 include all games between those positions
%     in the 'games:' list (not alphabetically).
%   - Variant lines for the same "slot" must be consecutive.

\begin{pcvstack}[boxed]

%%% -- Procedure header (one variant per game/reduction) ----------------------

    \procedure[linenumbering]{Game $\tfgamename{G0}$}{ %:tags: G0
    \procedure[linenumbering]{Game $\tfgamename{G1}$}{ %:tags: G1
    \procedure[linenumbering]{Reduction $\tfgamename{Red1}^{\Oracle}$}{ %:tags: Red1
    \procedure[linenumbering]{Game $\tfgamename{G2}$}{ %:tags: G2

%%% -- Procedure body ---------------------------------------------------------

        % G0, G1, G2 sample a key; Red1 uses an external oracle instead.
        % Note: G0,G1,G2 is an explicit list — the range G0-G2 would also
        % include Red1 (since Red1 sits between G1 and G2 in the games list).
        k \sample \{0,1\}^\lambda \\ %:tags: G0,G1,G2
        % G0: compute y using the key
        y \gets f(k) \\ %:tags: G0
        % G1, G2: sample y uniformly at random
        y \sample \{0,1\}^\lambda \\ %:tags: G1,G2
        % Red1: query the external oracle (no local key)
        y \gets \Oracle() \\ %:tags: Red1
        b' \gets \Adversary(y) \\
        \pcreturn b'
    }

\end{pcvstack}
"""

CRYPTOCODE_MACROS = r"""% Custom macros for this proof.
% Add your own \newcommand definitions here.

\newcommand{\Adversary}{\mathcal{A}}
\newcommand{\Bdversary}{\mathcal{B}}
\newcommand{\Oracle}{\mathcal{O}}
\newcommand{\sample}{\stackrel{{\scriptscriptstyle\$}}{\gets}}
"""

# ---------------------------------------------------------------------------
# nicodemus templates
# ---------------------------------------------------------------------------

NICODEMUS_YAML = r"""# TeXFrog proof configuration
#
# Edit this file to describe your game-hopping proof.
# Run `texfrog latex proof.yaml` to generate LaTeX output.
# Run `texfrog html build proof.yaml` to generate an interactive HTML viewer.

# Package profile: "cryptocode" (default) or "nicodemus".
package: nicodemus

# LaTeX macro files to \input (relative to this file).
# .sty/.cls files are copied but loaded via \usepackage instead of \input.
macros:
  - macros.tex

# Combined source file containing all game pseudocode (relative to this file).
source: games_source.tex

# Games and reductions, listed in proof order.
# Tag ranges like G0-G2 are resolved by POSITION in this list.
# IMPORTANT: the order here determines what ranges like G0-G1 mean.
games:
  - label: G0
    latex_name: 'G_0'
    description: 'The starting game.'

  - label: G1
    latex_name: 'G_1'
    description: 'Replace the real value with a random one.'

  # Reductions sit between the games they bridge.
  # 'reduction: true' displays them separately in the HTML viewer.
  # 'related_games' shows clean copies of those games alongside the reduction.
  - label: Red1
    latex_name: '\Bdversary'
    description: 'Reduction bridging \tfgamename{G0} and \tfgamename{G1}.'
    reduction: true
    related_games: [G0, G1]

  - label: G2
    latex_name: 'G_2'
    description: 'The final game, where the adversary has no advantage.'

# Per-game commentary shown in the HTML viewer and LaTeX harness.
commentary:
  G0: |
    The starting game.
  G1: |
    Games \tfgamename{G0} and \tfgamename{G1} differ in how $y$ is computed.
  Red1: |
    Reduction \tfgamename{Red1} queries an external oracle instead of
    computing $f(k)$ directly.
  G2: |
    The final game.

# Consolidated figures showing multiple games side by side.
figures:
  - label: all_games
    games: "G0,G1,G2,Red1"
"""

NICODEMUS_SOURCE = r"""% TeXFrog combined source file.
%
% Tag syntax (at end of line):  %:tags: label1,label2-label3
%   - Lines with no %:tags: comment appear in EVERY game.
%   - Lines tagged with labels appear only in those games.
%   - Ranges like G0-G1 include all games between those positions
%     in the 'games:' list (not alphabetically).
%   - Variant lines for the same "slot" must be consecutive.

\begin{tabular}[t]{l}
	\nicodemusboxNew{250pt}{%

%%% -- Procedure header (one variant per game/reduction) ----------------------

		\nicodemusheader{Game $\tfgamename{G0}$} %:tags: G0
		\nicodemusheader{Game $\tfgamename{G1}$} %:tags: G1
		\nicodemusheader{Reduction $\tfgamename{Red1}^{\Oracle}$} %:tags: Red1
		\nicodemusheader{Game $\tfgamename{G2}$} %:tags: G2

%%% -- Procedure body ---------------------------------------------------------

		\begin{nicodemus}
			% G0, G1, G2 sample a key; Red1 uses an external oracle instead.
			% Note: G0,G1,G2 is an explicit list — the range G0-G2 would also
			% include Red1 (since Red1 sits between G1 and G2 in the games list).
			\item $k \sample \{0,1\}^\lambda$ %:tags: G0,G1,G2
			% G0: compute y using the key
			\item $y \gets f(k)$ %:tags: G0
			% G1, G2: sample y uniformly at random
			\item $y \sample \{0,1\}^\lambda$ %:tags: G1,G2
			% Red1: query the external oracle (no local key)
			\item $y \gets \Oracle()$ %:tags: Red1
			\item $b' \gets \Adversary(y)$
			\item Return $b'$
		\end{nicodemus}%

	}%
\end{tabular}%
"""

NICODEMUS_MACROS = r"""% Custom macros for this proof.
% Add your own \newcommand definitions here.

\newcommand{\Adversary}{\mathcal{A}}
\newcommand{\Bdversary}{\mathcal{B}}
\newcommand{\Oracle}{\mathcal{O}}
\newcommand{\sample}{\stackrel{{\scriptscriptstyle\$}}{\gets}}
"""


def get_templates(package: str) -> dict[str, tuple[str, str]]:
    """Return template files for the given package profile.

    Args:
        package: ``"cryptocode"`` or ``"nicodemus"``.

    Returns:
        Dict mapping filename to ``(content, description)`` pairs.

    Raises:
        ValueError: If the package name is not recognised.
    """
    if package == "cryptocode":
        return {
            "proof.yaml": (CRYPTOCODE_YAML.lstrip("\n"), "proof configuration"),
            "games_source.tex": (CRYPTOCODE_SOURCE.lstrip("\n"), "combined game source"),
            "macros.tex": (CRYPTOCODE_MACROS.lstrip("\n"), "custom macros"),
        }
    elif package == "nicodemus":
        return {
            "proof.yaml": (NICODEMUS_YAML.lstrip("\n"), "proof configuration"),
            "games_source.tex": (NICODEMUS_SOURCE.lstrip("\n"), "combined game source"),
            "macros.tex": (NICODEMUS_MACROS.lstrip("\n"), "custom macros"),
        }
    else:
        raise ValueError(f"Unknown package '{package}'. Use 'cryptocode' or 'nicodemus'.")
