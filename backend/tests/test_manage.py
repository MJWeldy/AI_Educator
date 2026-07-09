from app import auth, manage
from app.models import Profile
from sqlalchemy import select


def test_create_list_and_delete_user(seeded_db, monkeypatch, capsys):
    # manage.py opens its own SessionLocal; point it at the test session.
    class _Ctx:
        def __enter__(self):
            return seeded_db

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(manage, "SessionLocal", lambda: _Ctx())
    monkeypatch.setattr(manage.getpass, "getpass", lambda _prompt="": "secret1")

    assert manage.create_user("alice") == 0
    profile = seeded_db.scalar(select(Profile).where(Profile.username == "alice"))
    assert profile is not None and auth.verify_password("secret1", profile.password_hash)

    # Duplicate (case-insensitive) is rejected.
    assert manage.create_user("Alice") == 1

    assert manage.list_users() == 0
    assert "alice" in capsys.readouterr().out

    assert manage.delete_user("alice") == 0
    assert seeded_db.scalar(select(Profile).where(Profile.username == "alice")) is None
    assert manage.delete_user("alice") == 1  # already gone
