import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")  # in-memory
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
