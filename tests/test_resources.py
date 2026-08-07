"""Tests for bundled package resources and how they are located.

These tests pin the *mechanism* (``importlib.resources`` over a declared
subpackage) rather than an on-disk path.  A path-based test passes in a source
checkout whether or not the file is actually declared in ``package-data``,
which is exactly how issue #20 --- ``nicodemus.sty`` missing from wheel
installs --- reached a release with a green test suite.
"""

from __future__ import annotations

import importlib.resources
from pathlib import Path

import pytest

from texfrog._resources import read_package_resource

# tomllib is stdlib only from 3.11; the project supports 3.10, where the
# packaging assertion below simply doesn't run (CI covers 3.11-3.14 as well).
try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10
    tomllib = None

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Bundled LaTeX packages that ``texfrog init`` writes into a scaffold, with a
# marker proving the real file (not, say, a symlink stub) was read.
_BUNDLED_STY = {
    "texfrog.sty": r"\ProvidesPackage{texfrog}",
    "nicodemus.sty": r"\ProvidesPackage{nicodemus}",
}


# ---------------------------------------------------------------------------
# read_package_resource
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name, marker", sorted(_BUNDLED_STY.items()))
def test_read_package_resource_returns_sty_contents(name: str, marker: str):
    content = read_package_resource("texfrog.resources", name)
    assert marker in content
    # A symlink that was checked out as a plain text file (e.g. a Windows
    # clone without symlink support) would yield only its target path.
    assert len(content) > 1000


@pytest.mark.parametrize("name", ["style.css", "app.js"])
def test_read_package_resource_reads_html_templates(name: str):
    """The HTML pipeline's static assets go through the same accessor."""
    assert len(read_package_resource("texfrog.output.templates", name)) > 0


def test_read_package_resource_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        read_package_resource("texfrog.resources", "no-such-file.sty")


def test_read_package_resource_missing_package_raises():
    with pytest.raises(ModuleNotFoundError):
        read_package_resource("texfrog.not_a_package", "anything.sty")


# ---------------------------------------------------------------------------
# Packaging declarations
# ---------------------------------------------------------------------------


def test_resources_are_reachable_as_package_data():
    """``texfrog.resources`` must be an importable package, not a bare dir.

    ``[tool.setuptools.packages.find]`` only picks up directories with an
    ``__init__.py``; without one the ``.sty`` files are silently dropped from
    the wheel even though ``package-data`` names them.
    """
    files = importlib.resources.files("texfrog.resources")
    for name in _BUNDLED_STY:
        assert files.joinpath(name).is_file()


@pytest.mark.skipif(tomllib is None, reason="tomllib requires Python 3.11+")
def test_pyproject_declares_sty_package_data():
    """The wheel only carries the ``.sty`` files if ``package-data`` says so.

    Nothing else in the suite fails if this declaration is deleted, because
    every other lookup resolves against the source tree.
    """
    pyproject = tomllib.loads(
        (_PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    setuptools_cfg = pyproject["tool"]["setuptools"]
    assert "*.sty" in setuptools_cfg["package-data"]["texfrog.resources"]
    # packages.find must also match the subpackage.
    assert setuptools_cfg["packages"]["find"]["include"] == ["texfrog*"]


def test_bundled_texfrog_sty_matches_canonical_latex_copy():
    """``texfrog/resources/texfrog.sty`` mirrors the canonical ``latex/`` file.

    ``latex/texfrog.sty`` is the copy the README tells non-Python users to
    download, and the packaged resource is a symlink to it that build backends
    dereference.  If the two ever diverge, pip users get a different package
    from the one documented.
    """
    canonical = (_PROJECT_ROOT / "latex" / "texfrog.sty").read_text(encoding="utf-8")
    assert read_package_resource("texfrog.resources", "texfrog.sty") == canonical
