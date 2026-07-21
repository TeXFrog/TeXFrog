"""Package profile definitions for TeXFrog.

Each pseudocode LaTeX package (cryptocode, nicodemus, algpseudocodex, etc.)
has different
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

    procedure_header_cmd: str | None = None
    """LaTeX command name (without backslash) for procedure headers.

    Lines starting with this command are treated as structural headers
    and are never wrapped with ``\\tfchanged``.  ``None`` if the package
    uses structural braces (``endswith("{")``) to mark headers instead.
    """

    line_counter_name: str | None = None
    """Name of the LaTeX counter this package uses for line numbers, or
    ``None`` if the package does not number lines.

    When set (``"ALG@line"`` for algpseudocodex), a cropped HTML render
    injects ``\\setcounter{<name>}{N}`` before each kept segment so the kept
    lines keep their ABSOLUTE numbers from the full listing (numbers jump
    across a stub instead of renumbering contiguously), matching the LaTeX
    crop-render's line-count pass in ``texfrog.sty``.
    """

    # -- Derived macro definitions ------------------------------------------

    def html_tfchanged(self) -> str:
        r"""``\newcommand`` definition for the HTML wrapper."""
        if self.math_mode_content:
            return (
                r"\newcommand{\tfchanged}[1]{"
                r"\ifmmode\highlightbox{\ensuremath{#1}}"
                r"\else\highlightbox{#1}\fi}"
            )
        return r"\newcommand{\tfchanged}[1]{\highlightbox{#1}}"

    def html_tfremoved(self) -> str:
        r"""``\newcommand`` definition for the HTML wrapper."""
        if self.math_mode_content:
            return (
                r"\newcommand{\tfremoved}[1]{"
                r"\ifmmode\textcolor{red}{\ensuremath{#1}}"
                r"\else\textcolor{red}{#1}\fi}"
            )
        return r"\newcommand{\tfremoved}[1]{\textcolor{red}{#1}}"

    def html_tfgamelabel(self) -> str:
        r"""``\newcommand`` definition for the HTML wrapper."""
        if self.gamelabel_comment_cmd:
            return (
                r"\newcommand{\tfgamelabel}[2]{#2 "
                + self.gamelabel_comment_cmd
                + r"{#1}}"
            )
        return (
            r"\newcommand{\tfniccommentseparator}"
            r"{{\color{black!65}\smash{\textbackslash\!\!\textbackslash\hspace{0.1em}}}}"
            "\n"
            r"\newcommand{\tfniccodecomment}[1]"
            r"{{\scriptsize{\hfill\tfniccommentseparator{#1}}}}"
            "\n"
            r"\newcommand{\tfgamelabel}[2]{#2 \tfniccodecomment{#1}}"
        )

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
        return (
            r"\providecommand{\tfniccommentseparator}"
            r"{{\color{black!65}\smash{\textbackslash\!\!\textbackslash\hspace{0.1em}}}}"
            "\n"
            r"\providecommand{\tfniccodecomment}[1]"
            r"{{\scriptsize{\hfill\tfniccommentseparator{#1}}}}"
            "\n"
            r"\providecommand{\tfgamelabel}[2]{#2 \tfniccodecomment{#1}}"
        )

    def html_tfsegmentstub(self) -> str:
        r"""Return the \tfsegmentstub definition for the HTML wrapper.

        Mirrors the three ``\tfsegmentstub`` definitions in ``latex/texfrog.sty``
        exactly, so the HTML output matches the PDF:

        - cryptocode (``has_line_separators``): math content terminated by
          ``\\`` (cryptocode's pchstack lines are ``\\``-separated).
        - nicodemus (``gamelabel_comment_cmd is None``): ``\item``-prefixed,
          since nicodemus is an ``\item``-based list environment where
          ``\Statex`` is undefined.
        - algpseudocodex (otherwise): ``\Statex``-prefixed unnumbered
          continuation line.

        ``\ensuremath`` (not literal ``$...$``) is required for ``\cdots``:
        cryptocode's procedure body is already in implicit math mode, so a
        literal ``$`` would toggle back out to text mode mid-line.
        """
        body = r"{\color{black!55}\ensuremath{\cdots}~\textit{#1~(unchanged)}~\ensuremath{\cdots}}"
        if self.has_line_separators:  # cryptocode: math + \\ separated lines
            return r"\newcommand{\tfsegmentstub}[1]{" + body + r" \\}"
        if self.gamelabel_comment_cmd is None:  # nicodemus: \item-based list env
            return r"\newcommand{\tfsegmentstub}[1]{\item " + body + r"}"
        # algpseudocodex: unnumbered continuation line. algpseudocodex
        # \pretocmd's its line-closing hook \algpx@endCodeCommand onto
        # \State/\If/... but NOT onto \Statex, so a stub directly after a
        # \State would push that \State's content below its own line number.
        # Run the hook first (guarded, catcode-agnostic via \csname since the
        # HTML preamble has no \makeatletter) so the preceding line renders
        # normally. Mirrors the base \tfsegmentstub in latex/texfrog.sty.
        hook = (
            r"\ifcsname algpx@endCodeCommand\endcsname"
            r"\csname algpx@endCodeCommand\endcsname\fi"
        )
        return r"\newcommand{\tfsegmentstub}[1]{" + hook + r"\Statex " + body + r"}"

    def procedure_header_def(self) -> str | None:
        r"""``\providecommand`` definition for the procedure header command.

        Returns ``None`` if the profile has no procedure header command.
        """
        if self.procedure_header_cmd is None:
            return None
        return (
            rf"\providecommand{{\{self.procedure_header_cmd}}}"
            r"[1]{\textbf{#1}}"
        )


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
        procedure_header_cmd="nicodemusheader",
    ),
    "algpseudocodex": PackageProfile(
        name="algpseudocodex",
        preamble_lines=(
            r"\usepackage{algpseudocodex}",
        ),
        has_line_separators=False,
        math_mode_content=False,
        gamelabel_comment_cmd=r"\Comment",
        # \Procedure is defined by algpseudocodex itself; procedure_header_def()'s
        # \providecommand is a no-op here (already defined) — this name only
        # drives wrap_changed_line()'s header-skip detection.
        procedure_header_cmd="Procedure",
        line_counter_name="ALG@line",
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
