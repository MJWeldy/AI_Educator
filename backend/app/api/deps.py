from fastapi import Depends, Request
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Profile

PROFILE_COOKIE = "educator_profile"


def current_profile_id(request: Request, db: Session = Depends(get_db)) -> int:
    """Active profile from the browser cookie; falls back to the default
    profile (id 1, seeded by the loader) when absent or stale."""
    raw = request.cookies.get(PROFILE_COOKIE, "")
    if raw.isdigit() and db.get(Profile, int(raw)) is not None:
        return int(raw)
    return 1
