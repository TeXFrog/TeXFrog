"""Tests for package profile definitions and lookup."""

from __future__ import annotations

import pytest

from texfrog.packages import BUILTIN_PROFILES, PackageProfile, get_profile


# ---------------------------------------------------------------------------
# get_profile lookup
# ---------------------------------------------------------------------------


class TestGetProfile:
    """Tests for the get_profile() function."""

    def test_get_cryptocode(self):
        profile = get_profile("cryptocode")
        assert profile.name == "cryptocode"

    def test_get_nicodemus(self):
        profile = get_profile("nicodemus")
        assert profile.name == "nicodemus"

    def test_unknown_profile_raises(self):
        with pytest.raises(ValueError, match="Unknown package profile 'bogus'"):
            get_profile("bogus")

    def test_unknown_profile_lists_available(self):
        with pytest.raises(ValueError, match="cryptocode"):
            get_profile("bogus")

    def test_builtin_profiles_match_get_profile(self):
        for name, profile in BUILTIN_PROFILES.items():
            assert get_profile(name) is profile


# ---------------------------------------------------------------------------
# Cryptocode profile properties
# ---------------------------------------------------------------------------


class TestCryptocodeProfile:
    """Tests for the cryptocode package profile."""

    @pytest.fixture()
    def profile(self):
        return get_profile("cryptocode")

    def test_has_line_separators(self, profile):
        assert profile.has_line_separators is True

    def test_math_mode_content(self, profile):
        assert profile.math_mode_content is True

    def test_gamelabel_comment_cmd(self, profile):
        assert profile.gamelabel_comment_cmd == r"\pccomment"

    def test_no_procedure_header_cmd(self, profile):
        assert profile.procedure_header_cmd is None

    def test_preamble_includes_cryptocode(self, profile):
        assert any("cryptocode" in line for line in profile.preamble_lines)


# ---------------------------------------------------------------------------
# Nicodemus profile properties
# ---------------------------------------------------------------------------


class TestNicodemusProfile:
    """Tests for the nicodemus package profile."""

    @pytest.fixture()
    def profile(self):
        return get_profile("nicodemus")

    def test_no_line_separators(self, profile):
        assert profile.has_line_separators is False

    def test_no_math_mode_content(self, profile):
        assert profile.math_mode_content is False

    def test_no_gamelabel_comment_cmd(self, profile):
        assert profile.gamelabel_comment_cmd is None

    def test_procedure_header_cmd(self, profile):
        assert profile.procedure_header_cmd == "nicodemusheader"

    def test_preamble_includes_nicodemus(self, profile):
        assert any("nicodemus" in line for line in profile.preamble_lines)


# ---------------------------------------------------------------------------
# html_tfchanged
# ---------------------------------------------------------------------------


class TestHtmlTfchanged:
    """Tests for the html_tfchanged() method."""

    def test_math_mode_uses_ifmmode(self):
        profile = get_profile("cryptocode")
        result = profile.html_tfchanged()
        assert r"\ifmmode" in result
        assert r"\ensuremath" in result
        assert r"\highlightbox" in result

    def test_non_math_mode_no_ifmmode(self):
        profile = get_profile("nicodemus")
        result = profile.html_tfchanged()
        assert r"\ifmmode" not in result
        assert r"\ensuremath" not in result
        assert r"\highlightbox" in result

    def test_is_newcommand(self):
        for name in BUILTIN_PROFILES:
            result = get_profile(name).html_tfchanged()
            assert result.startswith(r"\newcommand{\tfchanged}")


# ---------------------------------------------------------------------------
# html_tfremoved
# ---------------------------------------------------------------------------


class TestHtmlTfremoved:
    """Tests for the html_tfremoved() method."""

    def test_math_mode_uses_ifmmode(self):
        profile = get_profile("cryptocode")
        result = profile.html_tfremoved()
        assert r"\ifmmode" in result
        assert r"\ensuremath" in result
        assert r"\textcolor{red}" in result

    def test_non_math_mode_no_ifmmode(self):
        profile = get_profile("nicodemus")
        result = profile.html_tfremoved()
        assert r"\ifmmode" not in result
        assert r"\textcolor{red}" in result

    def test_is_newcommand(self):
        for name in BUILTIN_PROFILES:
            result = get_profile(name).html_tfremoved()
            assert result.startswith(r"\newcommand{\tfremoved}")


# ---------------------------------------------------------------------------
# html_tfgamelabel
# ---------------------------------------------------------------------------


class TestHtmlTfgamelabel:
    """Tests for the html_tfgamelabel() method."""

    def test_with_comment_cmd(self):
        profile = get_profile("cryptocode")
        result = profile.html_tfgamelabel()
        assert r"\pccomment" in result
        assert r"\tfgamelabel" in result

    def test_without_comment_cmd_uses_custom_comment(self):
        profile = get_profile("nicodemus")
        result = profile.html_tfgamelabel()
        assert r"\tfniccodecomment" in result
        assert r"\tfniccommentseparator" in result
        assert r"\tfgamelabel" in result

    def test_is_newcommand(self):
        for name in BUILTIN_PROFILES:
            result = get_profile(name).html_tfgamelabel()
            assert r"\newcommand" in result


# ---------------------------------------------------------------------------
# harness_tfchanged
# ---------------------------------------------------------------------------


class TestHarnessTfchanged:
    """Tests for the harness_tfchanged() method."""

    def test_math_mode_wraps_in_dollars(self):
        profile = get_profile("cryptocode")
        result = profile.harness_tfchanged()
        assert r"$#1$" in result
        assert r"\colorbox{blue!15}" in result

    def test_non_math_mode_no_dollars(self):
        profile = get_profile("nicodemus")
        result = profile.harness_tfchanged()
        assert r"$#1$" not in result
        assert r"\colorbox{blue!15}{#1}" in result

    def test_is_providecommand(self):
        for name in BUILTIN_PROFILES:
            result = get_profile(name).harness_tfchanged()
            assert result.startswith(r"\providecommand{\tfchanged}")


# ---------------------------------------------------------------------------
# harness_tfgamelabel
# ---------------------------------------------------------------------------


class TestHarnessTfgamelabel:
    """Tests for the harness_tfgamelabel() method."""

    def test_with_comment_cmd(self):
        profile = get_profile("cryptocode")
        result = profile.harness_tfgamelabel()
        assert r"\pccomment" in result

    def test_without_comment_cmd(self):
        profile = get_profile("nicodemus")
        result = profile.harness_tfgamelabel()
        assert r"\tfniccodecomment" in result

    def test_is_providecommand(self):
        for name in BUILTIN_PROFILES:
            result = get_profile(name).harness_tfgamelabel()
            assert r"\providecommand" in result


# ---------------------------------------------------------------------------
# procedure_header_def
# ---------------------------------------------------------------------------


class TestProcedureHeaderDef:
    """Tests for the procedure_header_def() method."""

    def test_none_when_no_header_cmd(self):
        profile = get_profile("cryptocode")
        assert profile.procedure_header_def() is None

    def test_returns_def_when_header_cmd(self):
        profile = get_profile("nicodemus")
        result = profile.procedure_header_def()
        assert result is not None
        assert r"\providecommand" in result
        assert "nicodemusheader" in result
        assert r"\textbf{#1}" in result
