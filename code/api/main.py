"""The ASGI app built from environment variables (used by uvicorn locally and by Vercel)."""

from .app import create_app

app = create_app()
