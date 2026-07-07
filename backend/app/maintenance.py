"""Startup maintenance: database backups and schema migrations.

Order matters: back up first, then migrate. A backup is always taken when a
migration is about to change the schema; otherwise backups are throttled so
dev-server reloads don't churn the rotation.
"""

import logging
import sqlite3
import time
from datetime import datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect

from .config import BACKEND_DIR, DATA_DIR, settings
from .db import engine

log = logging.getLogger("educator.maintenance")

BACKUPS_DIR = DATA_DIR / "backups"
KEEP_BACKUPS = 14
THROTTLE_SECONDS = 6 * 3600


def _db_path() -> Path | None:
    url = settings.database_url
    if not url.startswith("sqlite:///"):
        return None
    return Path(url.removeprefix("sqlite:///"))


def backup_database(force: bool = False) -> Path | None:
    """Copy the SQLite DB into data/backups/ via the online backup API
    (safe under WAL). Keeps the newest KEEP_BACKUPS files."""
    src_path = _db_path()
    if src_path is None or not src_path.exists() or src_path.stat().st_size == 0:
        return None

    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    existing = sorted(BACKUPS_DIR.glob("educator-*.db"))
    if not force and existing:
        newest_age = time.time() - existing[-1].stat().st_mtime
        if newest_age < THROTTLE_SECONDS:
            return None

    dest = BACKUPS_DIR / f"educator-{datetime.now():%Y%m%d-%H%M%S}.db"
    src = sqlite3.connect(src_path)
    dst = sqlite3.connect(dest)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()

    for old in sorted(BACKUPS_DIR.glob("educator-*.db"))[:-KEEP_BACKUPS]:
        old.unlink()
    log.info("backed up database to %s", dest.name)
    return dest


def alembic_config() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    return cfg


def run_migrations() -> None:
    """Bring the schema to head. Pre-Alembic databases (created by the old
    create_all path) are stamped as baseline first. A forced backup precedes
    any real schema change."""
    cfg = alembic_config()
    script = ScriptDirectory.from_config(cfg)
    head = script.get_current_head()

    with engine.connect() as conn:
        current = MigrationContext.configure(conn).get_current_revision()
        has_tables = "topics" in inspect(conn).get_table_names()

    if current is None and has_tables:
        # Existing DB from before migrations were introduced: its schema is
        # the baseline by construction, so just record that fact.
        command.stamp(cfg, script.get_base())
        with engine.connect() as conn:
            current = MigrationContext.configure(conn).get_current_revision()

    if current != head:
        backup_database(force=True)
        command.upgrade(cfg, "head")
