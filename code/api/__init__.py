"""Aegis :: api — the HTTP application layer.

Responsibilities:
    * Expose the FastAPI application and its HTTP endpoints.
    * Handle registration/authentication, vault creation and payload upload,
      timing configuration, trustee designation, the one-action check-in
      confirmation, and (post-release) K-of-N reconstruction + decryption.
    * Validate requests/responses (Pydantic schemas) and wire together the
      crypto, scheduler, vault, and notifications packages.

This layer holds no business rules of its own beyond transport and validation;
it delegates to the domain packages.

Week 1 status: scaffold only.
"""

__all__: list[str] = []
