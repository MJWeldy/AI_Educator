from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import auth
from ..config import settings
from ..db import get_db
from ..models import Profile

router = APIRouter(prefix="/api/auth", tags=["auth"])

MIN_PASSWORD = 6
COOKIE_MAX_AGE = auth.SESSION_DAYS * 24 * 3600


class Credentials(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str | None
    name: str


class MeOut(BaseModel):
    require_auth: bool
    user: UserOut | None


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        auth.SESSION_COOKIE,
        token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        path="/",
    )


def _user_out(profile: Profile) -> UserOut:
    return UserOut(id=profile.id, username=profile.username, name=profile.name)


@router.get("/me", response_model=MeOut)
def me(request: Request, db: Session = Depends(get_db)):
    """Always 200 so the frontend can branch. user is null when not logged in."""
    profile = None
    if settings.require_auth:
        pid = auth.profile_id_for_token(db, request.cookies.get(auth.SESSION_COOKIE))
        if pid is not None:
            profile = db.get(Profile, pid)
    return MeOut(require_auth=settings.require_auth, user=_user_out(profile) if profile else None)


@router.post("/register", response_model=UserOut)
def register(body: Credentials, response: Response, db: Session = Depends(get_db)):
    if not settings.require_auth:
        raise HTTPException(409, "accounts are only used in server mode")
    username = body.username.strip()
    if not username:
        raise HTTPException(400, "username required")
    if len(body.password) < MIN_PASSWORD:
        raise HTTPException(400, f"password must be at least {MIN_PASSWORD} characters")
    # Case-insensitive uniqueness so "Alice" and "alice" can't collide.
    exists = db.scalar(
        select(Profile).where(func.lower(Profile.username) == username.lower())
    )
    if exists is not None:
        raise HTTPException(409, "that username is taken")
    profile = Profile(name=username[:40], username=username, password_hash=auth.hash_password(body.password))
    db.add(profile)
    db.commit()
    _set_session_cookie(response, auth.create_session(db, profile.id))
    return _user_out(profile)


@router.post("/login", response_model=UserOut)
def login(body: Credentials, response: Response, db: Session = Depends(get_db)):
    if not settings.require_auth:
        raise HTTPException(409, "accounts are only used in server mode")
    profile = db.scalar(
        select(Profile).where(func.lower(Profile.username) == body.username.strip().lower())
    )
    if profile is None or not auth.verify_password(body.password, profile.password_hash):
        raise HTTPException(401, "wrong username or password")
    _set_session_cookie(response, auth.create_session(db, profile.id))
    return _user_out(profile)


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    auth.destroy_session(db, request.cookies.get(auth.SESSION_COOKIE))
    response.delete_cookie(auth.SESSION_COOKIE, path="/")
    return {"ok": True}
