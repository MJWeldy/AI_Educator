"""Persisted async job runner.

Jobs live in the `jobs` table so long-running work (textbook ingestion)
survives restarts: at startup any queued/running job is resumed. Handlers
are async callables keyed by job kind; each stage checkpoints its own
progress, so resuming is cheap.
"""

import asyncio
import logging
import traceback
from collections.abc import Awaitable, Callable

from sqlalchemy import select

from .db import SessionLocal
from .models import Job

log = logging.getLogger("educator.jobs")

HANDLERS: dict[str, Callable[[int], Awaitable[None]]] = {}
_tasks: set[asyncio.Task] = set()


def handler(kind: str):
    def wrap(fn):
        HANDLERS[kind] = fn
        return fn

    return wrap


def enqueue(db, kind: str, payload: dict) -> Job:
    job = Job(kind=kind, payload=payload, status="queued")
    db.add(job)
    db.commit()
    _spawn(job.id)
    return job


def _spawn(job_id: int) -> None:
    task = asyncio.create_task(_execute(job_id))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def _execute(job_id: int) -> None:
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is None or job.status in ("done", "cancelled"):
            return
        kind = job.kind
        fn = HANDLERS.get(kind)
        if fn is None:
            job.status = "failed"
            job.error = f"no handler for job kind {kind!r}"
            db.commit()
            return
        job.status = "running"
        db.commit()

    try:
        await fn(job_id)
    except Exception as e:  # noqa: BLE001 — job failures must be recorded, never raised
        log.exception("job %s failed", job_id)
        with SessionLocal() as db:
            job = db.get(Job, job_id)
            if job is not None:
                job.status = "failed"
                job.error = f"{e}\n{traceback.format_exc()[-2000:]}"
                db.commit()
        return

    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is not None and job.status == "running":
            job.status = "done"
            db.commit()


def set_progress(db, job_id: int, stage: str, current: int, total: int, message: str = "") -> None:
    job = db.get(Job, job_id)
    if job is not None:
        job.progress = {"stage": stage, "current": current, "total": total, "message": message}
        db.commit()


def resume_pending() -> None:
    """Called at startup: pick interrupted jobs back up."""
    with SessionLocal() as db:
        pending = db.scalars(select(Job.id).where(Job.status.in_(["queued", "running"]))).all()
    for job_id in pending:
        _spawn(job_id)
