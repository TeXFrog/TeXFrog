"""Inline templates for ``texfrog init``."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# cryptocode templates (pure LaTeX format)
# ---------------------------------------------------------------------------

CRYPTOCODE_TEX = r"""\documentclass{article}
\usepackage[margin=1in]{geometry}
\usepackage[n,advantage,operators,sets,adversary,landau,probability,notions,logic,ff,mm,primitives,events,complexity,oracles,asymptotics,keys]{cryptocode}
\usepackage[package=cryptocode]{texfrog}

\input{macros.tex}

%%% Game registration (order matters for range resolution)
\tfgames{myproof}{G0, G1, Red1, G2}
\tfgamename{myproof}{G0}{G_0}
\tfgamename{myproof}{G1}{G_1}
\tfgamename{myproof}{Red1}{\Bdversary}
\tfgamename{myproof}{G2}{G_2}

\tfdescription{myproof}{G0}{The starting game.}
\tfdescription{myproof}{G1}{Replace the real value with a random one.}
\tfdescription{myproof}{Red1}{Reduction bridging \tfgamename{myproof}{G0} and \tfgamename{myproof}{G1}.}
\tfdescription{myproof}{G2}{The final game, where the adversary has no advantage.}

\tfreduction{myproof}{Red1}
\tfrelatedgames{myproof}{Red1}{G0, G1}

\tfmacrofile{macros.tex}

\tfcommentary{myproof}{G0}{commentary/G0.tex}
\tfcommentary{myproof}{G1}{commentary/G1.tex}
\tfcommentary{myproof}{Red1}{commentary/Red1.tex}
\tfcommentary{myproof}{G2}{commentary/G2.tex}

%%% Proof source
%%% Lines tagged with \tfonly{labels}{content} appear only in the listed games.
%%% Ranges like G0-G1 include all games between those positions in the
%%% \tfgames list (not alphabetically).
\begin{tfsource}{myproof}
\begin{pcvstack}[boxed]
  \procedure[linenumbering]{%
    \tfonly{G0}{Game $\tfgamename{G0}$}%
    \tfonly{G1}{Game $\tfgamename{G1}$}%
    \tfonly{Red1}{Reduction $\tfgamename{Red1}^{\Oracle}$}%
    \tfonly{G2}{Game $\tfgamename{G2}$}%
  }{
    \tfonly{G0,G1,G2}{k \sample \{0,1\}^\lambda \\}
    \tfonly{G0}{y \gets f(k) \\}
    \tfonly{G1,G2}{y \sample \{0,1\}^\lambda \\}
    \tfonly{Red1}{y \gets \Oracle() \\}
    b' \gets \Adversary(y) \\
    \pcreturn b'
  }
\end{pcvstack}
\end{tfsource}

\begin{document}

\section*{My Game-Hopping Proof}

\subsection*{Game $\tfgamename{myproof}{G0}$}
\tfrendergame{myproof}{G0}

\subsection*{Game $\tfgamename{myproof}{G1}$}
\tfrendergame[diff=G0]{myproof}{G1}

\subsection*{Reduction $\tfgamename{myproof}{Red1}$}
\tfrendergame[diff=G1]{myproof}{Red1}

\subsection*{Game $\tfgamename{myproof}{G2}$}
\tfrendergame[diff=G1]{myproof}{G2}

\subsection*{Consolidated figure}
\tfrenderfigure{myproof}{G0,G1,G2}

\end{document}
"""

CRYPTOCODE_MACROS = r"""% Custom macros for this proof.
% Add your own \newcommand definitions here.

\newcommand{\Adversary}{\mathcal{A}}
\newcommand{\Bdversary}{\mathcal{B}}
\newcommand{\Oracle}{\mathcal{O}}
\newcommand{\sample}{\stackrel{{\scriptscriptstyle\$}}{\gets}}
"""

# ---------------------------------------------------------------------------
# nicodemus templates (pure LaTeX format)
# ---------------------------------------------------------------------------

NICODEMUS_TEX = r"""\documentclass{article}
\usepackage[margin=1in]{geometry}
\usepackage{nicodemus}
\usepackage[package=nicodemus]{texfrog}

\input{macros.tex}

%%% Game registration (order matters for range resolution)
\tfgames{myproof}{G0, G1, Red1, G2}
\tfgamename{myproof}{G0}{G_0}
\tfgamename{myproof}{G1}{G_1}
\tfgamename{myproof}{Red1}{\Bdversary}
\tfgamename{myproof}{G2}{G_2}

\tfdescription{myproof}{G0}{The starting game.}
\tfdescription{myproof}{G1}{Replace the real value with a random one.}
\tfdescription{myproof}{Red1}{Reduction bridging \tfgamename{myproof}{G0} and \tfgamename{myproof}{G1}.}
\tfdescription{myproof}{G2}{The final game, where the adversary has no advantage.}

\tfreduction{myproof}{Red1}
\tfrelatedgames{myproof}{Red1}{G0, G1}

\tfmacrofile{macros.tex}

\tfcommentary{myproof}{G0}{commentary/G0.tex}
\tfcommentary{myproof}{G1}{commentary/G1.tex}
\tfcommentary{myproof}{Red1}{commentary/Red1.tex}
\tfcommentary{myproof}{G2}{commentary/G2.tex}

%%% Proof source
%%% Lines tagged with \tfonly{labels}{content} appear only in the listed games.
%%% Ranges like G0-G1 include all games between those positions in the
%%% \tfgames list (not alphabetically).
\begin{tfsource}{myproof}
\begin{tabular}[t]{l}
	\nicodemusboxNew{250pt}{%
		\tfonly{G0}{\nicodemusheader{Game $\tfgamename{G0}$}}
		\tfonly{G1}{\nicodemusheader{Game $\tfgamename{G1}$}}
		\tfonly{Red1}{\nicodemusheader{Reduction $\tfgamename{Red1}^{\Oracle}$}}
		\tfonly{G2}{\nicodemusheader{Game $\tfgamename{G2}$}}
		\begin{nicodemus}
			\tfonly{G0,G1,G2}{\item $k \sample \{0,1\}^\lambda$}
			\tfonly{G0}{\item $y \gets f(k)$}
			\tfonly{G1,G2}{\item $y \sample \{0,1\}^\lambda$}
			\tfonly{Red1}{\item $y \gets \Oracle()$}
			\item $b' \gets \Adversary(y)$
			\item Return $b'$
		\end{nicodemus}%
	}%
\end{tabular}%
\end{tfsource}

\begin{document}

\section*{My Game-Hopping Proof}

\subsection*{Game $\tfgamename{myproof}{G0}$}
\tfrendergame{myproof}{G0}

\subsection*{Game $\tfgamename{myproof}{G1}$}
\tfrendergame[diff=G0]{myproof}{G1}

\subsection*{Reduction $\tfgamename{myproof}{Red1}$}
\tfrendergame[diff=G1]{myproof}{Red1}

\subsection*{Game $\tfgamename{myproof}{G2}$}
\tfrendergame[diff=G1]{myproof}{G2}

\subsection*{Consolidated figure}
\tfrenderfigure{myproof}{G0,G1,G2}

\end{document}
"""

NICODEMUS_MACROS = r"""% Custom macros for this proof.
% Add your own \newcommand definitions here.

\newcommand{\Adversary}{\mathcal{A}}
\newcommand{\Bdversary}{\mathcal{B}}
\newcommand{\Oracle}{\mathcal{O}}
\newcommand{\sample}{\stackrel{{\scriptscriptstyle\$}}{\gets}}
"""

# ---------------------------------------------------------------------------
# Commentary file templates (shared by both packages)
# ---------------------------------------------------------------------------

COMMENTARY_G0 = r"""The starting game.
"""

COMMENTARY_G1 = r"""Games \tfgamename{myproof}{G0} and \tfgamename{myproof}{G1} differ in how $y$ is computed.
"""

COMMENTARY_RED1 = r"""Reduction \tfgamename{myproof}{Red1} queries an external oracle instead of
computing $f(k)$ directly.
"""

COMMENTARY_G2 = r"""The final game.
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
    commentary_files = {
        "commentary/G0.tex": (COMMENTARY_G0.lstrip("\n"), "commentary for G0"),
        "commentary/G1.tex": (COMMENTARY_G1.lstrip("\n"), "commentary for G1"),
        "commentary/Red1.tex": (COMMENTARY_RED1.lstrip("\n"), "commentary for Red1"),
        "commentary/G2.tex": (COMMENTARY_G2.lstrip("\n"), "commentary for G2"),
    }
    if package == "cryptocode":
        return {
            "proof.tex": (CRYPTOCODE_TEX.lstrip("\n"), "proof document"),
            "macros.tex": (CRYPTOCODE_MACROS.lstrip("\n"), "custom macros"),
            **commentary_files,
        }
    elif package == "nicodemus":
        return {
            "proof.tex": (NICODEMUS_TEX.lstrip("\n"), "proof document"),
            "macros.tex": (NICODEMUS_MACROS.lstrip("\n"), "custom macros"),
            **commentary_files,
        }
    else:
        raise ValueError(f"Unknown package '{package}'. Use 'cryptocode' or 'nicodemus'.")
