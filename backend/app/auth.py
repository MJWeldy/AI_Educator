"""Password hashing and server sessions for multi-user (server) mode.

Uses only the standard library — PBKDF2-HMAC-SHA256 for passwords and random
opaque tokens for sessions — so no new dependencies are pulled in. Sessions are
stored server-side (revocable on logout) rather than signed cookies, so no
signing secret is needed either.
"""

import hashlib
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from .models import AuthSession

SESSION_COOKIE = "educator_session"
SESSION_DAYS = 30
_PBKDF2_ITERATIONS = 200_000


class RateLimiter:
    """In-process sliding-window limiter, keyed by client. Enough to blunt
    password brute-forcing on a single-worker server; not a distributed limiter."""

    def __init__(self, max_attempts: int, window_seconds: float):
        self.max_attempts = max_attempts
        self.window = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        hits = [t for t in self._hits[key] if now - t < self.window]
        hits.append(now)
        self._hits[key] = hits
        return len(hits) <= self.max_attempts


login_limiter = RateLimiter(max_attempts=10, window_seconds=60.0)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    if not stored:
        return False
    try:
        _algo, iterations, salt_hex, hash_hex = stored.split("$")
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
        )
    except (ValueError, TypeError):
        return False
    return secrets.compare_digest(dk.hex(), hash_hex)


def create_session(db: Session, profile_id: int) -> str:
    token = secrets.token_urlsafe(32)
    db.add(
        AuthSession(
            token=token,
            profile_id=profile_id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS),
        )
    )
    db.commit()
    return token


def profile_id_for_token(db: Session, token: str | None) -> int | None:
    if not token:
        return None
    session = db.get(AuthSession, token)
    if session is None:
        return None
    expires = session.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        db.delete(session)
        db.commit()
        return None
    return session.profile_id


def destroy_session(db: Session, token: str | None) -> None:
    if not token:
        return
    session = db.get(AuthSession, token)
    if session is not None:
        db.delete(session)
        db.commit()
