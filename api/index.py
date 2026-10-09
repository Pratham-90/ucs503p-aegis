"""Vercel entrypoint (file-based Python function).

Exposes the FastAPI app defined in ``code/api``. The domain packages live in
``code/`` (pytest uses ``pythonpath = ["code"]``), so it is put first on sys.path.

This file sits in a top-level directory that is *also* called ``api`` (Vercel
requires it), so any already-imported ``api`` module is dropped before importing,
to make sure ``api.main`` resolves to ``code/api/main.py``.
"""

import importlib
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parent.parent / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))
sys.modules.pop("api", None)

app = importlib.import_module("api.main").app
