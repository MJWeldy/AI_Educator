from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (
    Attempt,
    DiagnosticSession,
    Profile,
    Task,
    UserTopicState,
    XpEntry,
)
from .deps import PROFILE_COOKIE, current_profile_id

router = APIRouter(prefix="/api/profiles", tags=["profiles"])

COOKIE_MAX_AGE = 10 * 365 * 24 * 3600


class ProfileOut(BaseModel):
    id: int
    name: str
    total_xp: int


class ProfilesOut(BaseModel):
    current_id: int
    profiles: list[ProfileOut]


def _all_profiles(db: Session) -> list[ProfileOut]:
    xp = dict(
        db.execute(
            select(XpEntry.profile_id, func.sum(XpEntry.amount)).group_by(XpEntry.profile_id)
        ).all()
    )
    return [
        ProfileOut(id=p.id, name=p.name, total_xp=xp.get(p.id, 0))
        for p in db.scalars(select(Profile).order_by(Profile.id))
    ]


@router.get("", response_model=ProfilesOut)
def list_profiles(
    db: Session = Depends(get_db), profile_id: int = Depends(current_profile_id)
):
    return ProfilesOut(current_id=profile_id, profiles=_all_profiles(db))


class ProfileIn(BaseModel):
    name: str


@router.post("", response_model=ProfileOut)
def create_profile(body: ProfileIn, db: Session = Depends(get_db)):
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "name required")
    profile = Profile(name=name[:40])
    db.add(profile)
    db.commit()
    return ProfileOut(id=profile.id, name=profile.name, total_xp=0)


@router.put("/{profile_id}", response_model=ProfileOut)
def rename_profile(profile_id: int, body: ProfileIn, db: Session = Depends(get_db)):
    profile = db.get(Profile, profile_id)
    if profile is None:
        raise HTTPException(404, "profile not found")
    if body.name.strip():
        profile.name = body.name.strip()[:40]
        db.commit()
    return ProfileOut(id=profile.id, name=profile.name, total_xp=0)


@router.post("/{profile_id}/select", response_model=ProfilesOut)
def select_profile(profile_id: int, response: Response, db: Session = Depends(get_db)):
    if db.get(Profile, profile_id) is None:
        raise HTTPException(404, "profile not found")
    response.set_cookie(
        PROFILE_COOKIE,
        str(profile_id),
        max_age=COOKIE_MAX_AGE,
        samesite="lax",
        path="/",
    )
    return ProfilesOut(current_id=profile_id, profiles=_all_profiles(db))


@router.delete("/{profile_id}")
def delete_profile(
    profile_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current: int = Depends(current_profile_id),
):
    profile = db.get(Profile, profile_id)
    if profile is None:
        raise HTTPException(404, "profile not found")
    if db.scalar(select(func.count()).select_from(Profile)) <= 1:
        raise HTTPException(409, "cannot delete the last profile")

    # All progress goes with the profile. Content (courses, lessons) is shared.
    # Order matters: attempts and XP entries reference tasks.
    for model in (UserTopicState, Attempt, XpEntry, Task, DiagnosticSession):
        for row in db.scalars(select(model).where(model.profile_id == profile_id)):
            db.delete(row)
    db.delete(profile)
    db.commit()
    if current == profile_id:
        response.delete_cookie(PROFILE_COOKIE, path="/")
    return {"ok": True}
