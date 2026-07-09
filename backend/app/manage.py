"""Owner CLI for managing accounts in server/web mode.

Run from the backend directory, e.g.:

    ../.venv/bin/python -m app.manage create-user alice
    ../.venv/bin/python -m app.manage list-users
    ../.venv/bin/python -m app.manage set-password alice
    ../.venv/bin/python -m app.manage delete-user alice

Passwords are prompted for (never passed on the command line). This is how you
provision friends' accounts when public sign-ups are closed (--web mode).
"""

import argparse
import getpass
import sys

from sqlalchemy import func, select

from . import auth
from .db import SessionLocal
from .models import AuthSession, Profile

MIN_PASSWORD = 6


def _find(db, username: str) -> Profile | None:
    return db.scalar(select(Profile).where(func.lower(Profile.username) == username.lower()))


def _prompt_password() -> str:
    while True:
        pw = getpass.getpass("Password: ")
        if len(pw) < MIN_PASSWORD:
            print(f"  password must be at least {MIN_PASSWORD} characters")
            continue
        if pw != getpass.getpass("Confirm: "):
            print("  passwords didn't match")
            continue
        return pw


def create_user(username: str) -> int:
    with SessionLocal() as db:
        if _find(db, username) is not None:
            print(f"error: username {username!r} is already taken")
            return 1
        password = _prompt_password()
        db.add(
            Profile(name=username[:40], username=username, password_hash=auth.hash_password(password))
        )
        db.commit()
        print(f"created account {username!r}")
    return 0


def set_password(username: str) -> int:
    with SessionLocal() as db:
        profile = _find(db, username)
        if profile is None:
            print(f"error: no account named {username!r}")
            return 1
        profile.password_hash = auth.hash_password(_prompt_password())
        # Log the user out everywhere so the old password can't linger.
        for s in db.scalars(select(AuthSession).where(AuthSession.profile_id == profile.id)):
            db.delete(s)
        db.commit()
        print(f"password updated for {username!r}")
    return 0


def delete_user(username: str) -> int:
    from .models import Attempt, DiagnosticSession, Enrollment, Task, UserTopicState, XpEntry

    with SessionLocal() as db:
        profile = _find(db, username)
        if profile is None:
            print(f"error: no account named {username!r}")
            return 1
        for model in (
            UserTopicState, Attempt, XpEntry, Task, DiagnosticSession, Enrollment, AuthSession,
        ):
            for row in db.scalars(select(model).where(model.profile_id == profile.id)):
                db.delete(row)
        db.delete(profile)
        db.commit()
        print(f"deleted account {username!r} and all its progress")
    return 0


def list_users() -> int:
    with SessionLocal() as db:
        accounts = db.scalars(
            select(Profile).where(Profile.username.is_not(None)).order_by(Profile.id)
        ).all()
        if not accounts:
            print("no accounts yet — create one with: create-user <name>")
            return 0
        for p in accounts:
            print(f"  {p.id:>3}  {p.username}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.manage", description="Manage Educator accounts")
    sub = parser.add_subparsers(dest="command", required=True)
    for cmd in ("create-user", "set-password", "delete-user"):
        p = sub.add_parser(cmd)
        p.add_argument("username")
    sub.add_parser("list-users")

    args = parser.parse_args(argv)
    if args.command == "create-user":
        return create_user(args.username)
    if args.command == "set-password":
        return set_password(args.username)
    if args.command == "delete-user":
        return delete_user(args.username)
    if args.command == "list-users":
        return list_users()
    return 1


if __name__ == "__main__":
    sys.exit(main())
