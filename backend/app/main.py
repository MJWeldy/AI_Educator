from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import models  # noqa: F401 — register tables on Base
from . import jobs
from .api import (
    auth,
    courses,
    diagnostic,
    documents,
    learn,
    llm,
    profiles,
    settings as settings_api,
    stats,
    tasks,
    topics,
)
from .ingest import pipeline  # noqa: F401 — registers the ingest_document job handler
from .config import settings
from .content import checking
from .content.loader import load_seed
from .db import SessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio

    if settings.testing:
        # Tests supply their own in-memory DB via dependency overrides;
        # never touch the real data directory from the test suite.
        yield
        return

    from . import maintenance

    maintenance.backup_database()
    maintenance.run_migrations()
    with SessionLocal() as db:
        load_seed(db)
    jobs.set_loop(asyncio.get_running_loop())
    jobs.resume_pending()
    checking.warm_pool()
    yield


app = FastAPI(title="Educator", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(topics.router)
app.include_router(learn.router)
app.include_router(tasks.router)
app.include_router(stats.router)
app.include_router(diagnostic.router)
app.include_router(llm.router)
app.include_router(settings_api.router)
app.include_router(documents.router)
app.include_router(profiles.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


if settings.frontend_dist.is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=settings.frontend_dist / "assets"),
        name="assets",
    )

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        # Client-side routes all serve the SPA shell.
        from fastapi.responses import FileResponse

        file = settings.frontend_dist / path
        if path and file.is_file():
            return FileResponse(file)
        return FileResponse(settings.frontend_dist / "index.html")
