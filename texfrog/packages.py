"""Package profile definitions for TeXFrog.

Each pseudocode LaTeX package (cryptocode, nicodemus, etc.) has different
conventions for line separators, content mode, and available macros.
A :class:`PackageProfile` captures these differences so that the rest of
TeXFrog can generate correct output regardless of the package in use.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PackageProfile:
    """Configuration for a specific LaTeX pseudocode package."""

    name: str
    preamble_lines: tuple[str, ...]
    """``\\usepackage`` lines to include in the HTML wrapper preamble."""

    has_line_separators: bool
    """True if pseudocode lines end with ``\\\\`` (e.g. cryptocode).

    When True, trailing ``\\\\`` is stripped from the last filtered line and
    ``\\\\`` is inserted between lines in consolidated figures.
    """

    math_mode_content: bool
    """True if pseudocode content is rendered in math mode (e.g. inside
    cryptocode's ``\\procedure`` environment).

    Affects whether ``\\tfchanged`` wraps content in ``\\ensuremath`` /
    ``$...$``.
    """

    gamelabel_comment_cmd: str | None
    """LaTeX macro for rendering inline game-label comments in consolidated
    figures (e.g. ``"\\pccomment"`` for cryptocode).  ``None`` if the package
    has no built-in comment macro.
    """

    # -- Derived macro definitions ------------------------------------------

    def html_tfchanged(self) -> str:
        r"""``\newcommand`` definition for the HTML wrapper."""
        if self.math_mode_content:
            return r"\newcommand{\tfchanged}[1]{\highlightbox{\ensuremath{#1}}}"
        return r"\newcommand{\tfchanged}[1]{\highlightbox{#1}}"

    def html_tfremoved(self) -> str:
        r"""``\newcommand`` definition for the HTML wrapper."""
        if self.math_mode_content:
            return r"\newcommand{\tfremoved}[1]{\textcolor{red}{\ensuremath{#1}}}"
        return r"\newcommand{\tfremoved}[1]{\textcolor{red}{#1}}"

    def html_tfgamelabel(self) -> str:
        r"""``\newcommand`` definition for the HTML wrapper."""
        if self.gamelabel_comment_cmd:
            return (
                r"\newcommand{\tfgamelabel}[2]{#2 "
                + self.gamelabel_comment_cmd
                + r"{#1}}"
            )
        return r"\newcommand{\tfgamelabel}[2]{#2}"

    def harness_tfchanged(self) -> str:
        r"""``\providecommand`` definition for the LaTeX harness."""
        if self.math_mode_content:
            return r"\providecommand{\tfchanged}[1]{\colorbox{blue!15}{$#1$}}"
        return r"\providecommand{\tfchanged}[1]{\colorbox{blue!15}{#1}}"

    def harness_tfgamelabel(self) -> str:
        r"""``\providecommand`` definition for the LaTeX harness."""
        if self.gamelabel_comment_cmd:
            return (
                r"\providecommand{\tfgamelabel}[2]{#2 "
                + self.gamelabel_comment_cmd
                + r"{#1}}"
            )
        return r"\providecommand{\tfgamelabel}[2]{#2}"


# ---------------------------------------------------------------------------
# Built-in profiles
# ---------------------------------------------------------------------------

BUILTIN_PROFILES: dict[str, PackageProfile] = {
    "cryptocode": PackageProfile(
        name="cryptocode",
        preamble_lines=(
            r"\usepackage[n,advantage,operators,sets,adversary,landau,probability,"
            r"notions,logic,ff,mm,primitives,events,complexity,oracles,asymptotics,"
            r"keys]{cryptocode}",
        ),
        has_line_separators=True,
        math_mode_content=True,
        gamelabel_comment_cmd=r"\pccomment",
    ),
    "nicodemus": PackageProfile(
        name="nicodemus",
        preamble_lines=(
            r"\usepackage{nicodemus}",
        ),
        has_line_separators=False,
        math_mode_content=False,
        gamelabel_comment_cmd=None,
    ),
}


def get_profile(name: str) -> PackageProfile:
    """Look up a built-in package profile by name.

    Args:
        name: Profile name (e.g. ``"cryptocode"`` or ``"nicodemus"``).

    Returns:
        The corresponding :class:`PackageProfile`.

    Raises:
        ValueError: If the name is not recognised.
    """
    profile = BUILTIN_PROFILES.get(name)
    if profile is None:
        known = ", ".join(sorted(BUILTIN_PROFILES))
        raise ValueError(
            f"Unknown package profile '{name}'. "
            f"Available profiles: {known}"
        )
    return profile
