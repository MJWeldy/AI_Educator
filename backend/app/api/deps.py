from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .. import auth
from ..config import settings
from ..db import get_db
from ..models import Profile

PROFILE_COOKIE = "educator_profile"


def current_profile_id(request: Request, db: Session = Depends(get_db)) -> int:
    """The active profile for this request.

    Server mode: the logged-in account (from a signed-in session), 401 if none.
    Local mode: the browser-cookie profile, falling back to the default
    profile (id 1, seeded by the loader) when absent or stale."""
    if settings.require_auth:
        pid = auth.profile_id_for_token(db, request.cookies.get(auth.SESSION_COOKIE))
        if pid is None:
            raise HTTPException(401, "authentication required")
        return pid
    raw = request.cookies.get(PROFILE_COOKIE, "")
    if raw.isdigit() and db.get(Profile, int(raw)) is not None:
        return int(raw)
    return 1
