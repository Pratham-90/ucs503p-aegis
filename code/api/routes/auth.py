"""Owner registration and login (FR-1, NFR-SEC-3)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from vault.models import Owner

from ..config import Settings
from ..deps import current_owner, get_session, get_settings
from ..errors import APIError
from ..schemas import Credentials, OwnerOut
from ..security import clear_session_cookie, hash_password, make_session_token, set_session_cookie, verify_password

router = APIRouter(tags=["auth"])


@router.post("/auth/register", status_code=201, response_model=OwnerOut)
def register(body: Credentials, response: Response, session: Session = Depends(get_session),
             settings: Settings = Depends(get_settings)):
    email = body.email.lower()
    if session.execute(select(Owner.id).where(Owner.email == email)).first():
        raise APIError(409, "email_taken", "An account with this email already exists.")
    owner = Owner(email=email, password_hash=hash_password(body.password))
    session.add(owner)
    session.flush()
    set_session_cookie(response, make_session_token(owner.id, settings), settings)
    return OwnerOut(id=owner.id, email=owner.email)


@router.post("/auth/login", response_model=OwnerOut)
def login(body: Credentials, response: Response, session: Session = Depends(get_session),
          settings: Settings = Depends(get_settings)):
    owner = session.execute(select(Owner).where(Owner.email == body.email.lower())).scalar_one_or_none()
    if owner is None or not verify_password(owner.password_hash, body.password):
        raise APIError(401, "bad_credentials", "Email or password is incorrect.")
    set_session_cookie(response, make_session_token(owner.id, settings), settings)
    return OwnerOut(id=owner.id, email=owner.email)


@router.post("/auth/logout", status_code=204)
def logout(response: Response, settings: Settings = Depends(get_settings)):
    clear_session_cookie(response, settings)
    response.status_code = 204
    return response


@router.get("/me", response_model=OwnerOut)
def me(owner: Owner = Depends(current_owner)):
    return OwnerOut(id=owner.id, email=owner.email)
