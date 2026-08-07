"""Shared accessor for files bundled inside the ``texfrog`` distribution.

Package data is read through :mod:`importlib.resources` rather than paths
derived from ``__file__`` so that lookups work identically for editable
installs, wheels, and zipped installs.  Every bundled file the code reads at
runtime goes through :func:`read_package_resource`; see
``[tool.setuptools.package-data]`` in ``pyproject.toml`` for the manifest of
what is actually shipped.
"""

from __future__ import annotations

import importlib.resources


def read_package_resource(package: str, name: str) -> str:
    """Return the text of *name* bundled inside *package*.

    Args:
        package: Dotted name of the package holding the resource, e.g.
            ``"texfrog.resources"``.
        name: Filename of the resource within that package.

    Returns:
        The resource's contents, decoded as UTF-8.

    Raises:
        FileNotFoundError: If *package* ships no such resource.
    """
    return importlib.resources.files(package).joinpath(name).read_text(encoding="utf-8")
