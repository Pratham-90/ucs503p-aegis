"""pyproject.toml (read by Vercel) and requirements.txt (local/CI) must list the same runtime deps."""

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _names(specs):
    return {re.split(r"[\[<>=!~ ]", s.strip(), maxsplit=1)[0].lower() for s in specs if s.strip()}


def test_runtime_dependencies_match():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    requirements = [line for line in (ROOT / "requirements.txt").read_text().splitlines()
                    if line.strip() and not line.startswith("#")]
    assert _names(project["dependencies"]) - {"click"} == _names(requirements)
    assert project["requires-python"] == ">=3.12"
