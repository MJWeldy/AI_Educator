"""Migrations and backups."""

import sqlite3

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from app.db import Base
from app.maintenance import alembic_config


@pytest.fixture()
def migrated_engine(tmp_path):
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    cfg = alembic_config()
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")
    return create_engine(url)


def test_migrations_create_full_schema(migrated_engine):
    tables = set(inspect(migrated_engine).get_table_names())
    expected = set(Base.metadata.tables)
    assert expected <= tables, f"missing tables: {expected - tables}"


def test_migrations_match_models(migrated_engine):
    """Drift guard: after upgrading to head, autogenerate must find nothing
    left to do. If this fails, a model changed without a migration."""
    with migrated_engine.connect() as conn:
        ctx = MigrationContext.configure(
            conn, opts={"compare_type": True, "render_as_batch": True}
        )
        diff = compare_metadata(ctx, Base.metadata)
    assert diff == [], f"schema drift between models and migrations: {diff}"


def test_backup_and_rotation(tmp_path, monkeypatch):
    from app import maintenance

    db_path = tmp_path / "educator.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE t (x)")
    conn.execute("INSERT INTO t VALUES (42)")
    conn.commit()
    conn.close()

    monkeypatch.setattr(maintenance.settings, "database_url", f"sqlite:///{db_path}")
    monkeypatch.setattr(maintenance, "BACKUPS_DIR", tmp_path / "backups")
    monkeypatch.setattr(maintenance, "KEEP_BACKUPS", 3)

    dest = maintenance.backup_database()
    assert dest is not None and dest.exists()
    check = sqlite3.connect(dest)
    assert check.execute("SELECT x FROM t").fetchone() == (42,)
    check.close()

    # Throttled: an immediate second backup is skipped…
    assert maintenance.backup_database() is None
    # …but force always backs up, and rotation keeps only the newest N.
    import time

    for _ in range(4):
        time.sleep(1.1)  # distinct timestamped filenames
        assert maintenance.backup_database(force=True) is not None
    assert len(list((tmp_path / "backups").glob("educator-*.db"))) == 3


def test_backup_skips_missing_db(tmp_path, monkeypatch):
    from app import maintenance

    monkeypatch.setattr(
        maintenance.settings, "database_url", f"sqlite:///{tmp_path / 'absent.db'}"
    )
    monkeypatch.setattr(maintenance, "BACKUPS_DIR", tmp_path / "backups")
    assert maintenance.backup_database(force=True) is None
