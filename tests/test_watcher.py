"""Tests for texfrog.watcher."""

from __future__ import annotations

from pathlib import Path

import pytest

from texfrog.watcher import collect_watched_files


class TestCollectWatchedFiles:
    """Tests for collect_watched_files (tex format)."""

    def test_includes_tex_file(self, tmp_path: Path) -> None:
        tex_file = tmp_path / "proof.tex"
        tex_file.write_text(
            r"\tfgames{G0}" "\n"
            r"\begin{tfsource}{main}" "\n"
            "line\n"
            r"\end{tfsource}" "\n"
        )
        watched = collect_watched_files(tex_file)
        assert tex_file in watched

    def test_includes_macrofile(self, tmp_path: Path) -> None:
        tex_file = tmp_path / "proof.tex"
        macro = tmp_path / "macros.tex"
        macro.write_text("")
        tex_file.write_text(
            r"\tfmacrofile{macros.tex}" "\n"
            r"\tfgames{G0}" "\n"
            r"\begin{tfsource}{main}" "\n"
            "line\n"
            r"\end{tfsource}" "\n"
        )
        watched = collect_watched_files(tex_file)
        assert macro.resolve() in watched

    def test_includes_preamble(self, tmp_path: Path) -> None:
        tex_file = tmp_path / "proof.tex"
        preamble = tmp_path / "preamble.tex"
        preamble.write_text("")
        tex_file.write_text(
            r"\tfpreamble{preamble.tex}" "\n"
            r"\tfgames{G0}" "\n"
            r"\begin{tfsource}{main}" "\n"
            "line\n"
            r"\end{tfsource}" "\n"
        )
        watched = collect_watched_files(tex_file)
        assert preamble.resolve() in watched

    def test_includes_commentary(self, tmp_path: Path) -> None:
        tex_file = tmp_path / "proof.tex"
        commentary_dir = tmp_path / "commentary"
        commentary_dir.mkdir()
        comm_file = commentary_dir / "G0.tex"
        comm_file.write_text("commentary text")
        tex_file.write_text(
            r"\tfgames{G0}" "\n"
            r"\tfcommentary{G0}{commentary/G0.tex}" "\n"
            r"\begin{tfsource}{main}" "\n"
            "line\n"
            r"\end{tfsource}" "\n"
        )
        watched = collect_watched_files(tex_file)
        assert comm_file.resolve() in watched

    def test_includes_input_files(self, tmp_path: Path) -> None:
        tex_file = tmp_path / "proof.tex"
        input_file = tmp_path / "extra.tex"
        input_file.write_text("")
        tex_file.write_text(
            r"\input{extra.tex}" "\n"
            r"\tfgames{G0}" "\n"
            r"\begin{tfsource}{main}" "\n"
            "line\n"
            r"\end{tfsource}" "\n"
        )
        watched = collect_watched_files(tex_file)
        assert input_file.resolve() in watched

    def test_unreadable_file_returns_self_only(self, tmp_path: Path) -> None:
        tex_file = tmp_path / "proof.tex"
        # File doesn't exist yet — collect should handle gracefully
        tex_file.write_text("")
        watched = collect_watched_files(tex_file)
        assert tex_file in watched
