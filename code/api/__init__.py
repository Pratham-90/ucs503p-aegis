"""Aegis :: api — the FastAPI application (every route under ``/api``).

``app.create_app`` builds the app; ``main.app`` is the instance used by uvicorn
and by the Vercel function (``api/index.py``). Routes: auth (FR-1), vaults
(FR-2..FR-6), one-click check-in links (FR-6), trustee enrolment / portal /
blob (FR-4, FR-7, FR-8), cron tick (FR-5, FR-7), Demo Console, health.

The API never receives a plaintext payload, the AES key or a plaintext share,
and performs no payload cryptography (NFR-SEC-5). ``testing.ScriptedBrowser``
replays the client-side steps with the Python crypto for tests and metrics.
"""

__all__: list[str] = []
