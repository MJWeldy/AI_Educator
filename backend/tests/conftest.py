import os

os.environ["EDUCATOR_TESTING"] = "1"  # must precede any app import

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401 — register every table on Base before create_all
from app.db import Base


@pytest.fixture()
def db():
    # StaticPool + check_same_thread=False: one shared in-memory DB that
    # survives TestClient's worker threads.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture()
def seeded_db(db):
    from app.content.loader import load_seed

    load_seed(db)
    return db
