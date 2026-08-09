"""Smoke test: every Aegis package imports cleanly.

Week 1 has no behaviour to test yet — this exists so the package layout stays
importable (pytest resolves them via ``pythonpath = ["code"]`` in
pyproject.toml) and so there is a green test from day one. Real unit tests
arrive with each module's implementation.
"""

import importlib

import pytest

AEGIS_PACKAGES = ["crypto", "scheduler", "vault", "notifications", "api"]


@pytest.mark.parametrize("package_name", AEGIS_PACKAGES)
def test_package_imports(package_name: str) -> None:
    module = importlib.import_module(package_name)
    assert module.__doc__, f"{package_name} should document its responsibility"
    assert hasattr(module, "__all__"), f"{package_name} should define __all__"
