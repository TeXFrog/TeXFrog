"""Tests for texfrog.watcher."""

from __future__ import annotations

from pathlib import Path

import pytest

from texfrog.watcher import collect_watched_files


class TestCollectWatchedFiles:
    """Tests for collect_watched_files."""

    def test_includes_yaml_and_source(self, tmp_path: Path) -> None:
        yaml_file = tmp_path / "proof.yaml"
        source_file = tmp_path / "source.tex"
        source_file.write_text("line1\n")
        yaml_file.write_text(
            "source: source.tex\nmacros: []\n"
            "games:\n  - label: G0\n    latex_name: G_0\n    description: d\n"
        )
        watched = collect_watched_files(yaml_file)
        assert yaml_file in watched
        assert source_file.resolve() in watched

    def test_includes_macros(self, tmp_path: Path) -> None:
        yaml_file = tmp_path / "proof.yaml"
        macro = tmp_path / "macros.tex"
        macro.write_text("")
        yaml_file.write_text(
            "source: source.tex\nmacros:\n  - macros.tex\n"
            "games:\n  - label: G0\n    latex_name: G_0\n    description: d\n"
        )
        watched = collect_watched_files(yaml_file)
        assert macro.resolve() in watched

    def test_includes_preamble(self, tmp_path: Path) -> None:
        yaml_file = tmp_path / "proof.yaml"
        preamble = tmp_path / "preamble.tex"
        preamble.write_text("")
        yaml_file.write_text(
            "source: source.tex\npreamble: preamble.tex\nmacros: []\n"
            "games:\n  - label: G0\n    latex_name: G_0\n    description: d\n"
        )
        watched = collect_watched_files(yaml_file)
        assert preamble.resolve() in watched

    def test_invalid_yaml_returns_yaml_only(self, tmp_path: Path) -> None:
        yaml_file = tmp_path / "proof.yaml"
        yaml_file.write_text("{{{{bad yaml")
        watched = collect_watched_files(yaml_file)
        assert watched == {yaml_file}

    def test_non_dict_yaml_returns_yaml_only(self, tmp_path: Path) -> None:
        yaml_file = tmp_path / "proof.yaml"
        yaml_file.write_text("- just a list\n- not a dict\n")
        watched = collect_watched_files(yaml_file)
        assert watched == {yaml_file}

    def test_multiple_macros(self, tmp_path: Path) -> None:
        yaml_file = tmp_path / "proof.yaml"
        m1 = tmp_path / "macros.tex"
        m2 = tmp_path / "extra.sty"
        m1.write_text("")
        m2.write_text("")
        yaml_file.write_text(
            "source: source.tex\nmacros:\n  - macros.tex\n  - extra.sty\n"
            "games:\n  - label: G0\n    latex_name: G_0\n    description: d\n"
        )
        watched = collect_watched_files(yaml_file)
        assert m1.resolve() in watched
        assert m2.resolve() in watched

    def test_no_optional_fields(self, tmp_path: Path) -> None:
        """YAML with only source and games — no macros or preamble."""
        yaml_file = tmp_path / "proof.yaml"
        source_file = tmp_path / "source.tex"
        source_file.write_text("")
        yaml_file.write_text(
            "source: source.tex\n"
            "games:\n  - label: G0\n    latex_name: G_0\n    description: d\n"
        )
        watched = collect_watched_files(yaml_file)
        assert yaml_file in watched
        assert source_file.resolve() in watched
        assert len(watched) == 2
