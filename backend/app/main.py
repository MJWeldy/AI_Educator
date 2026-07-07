from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import models  # noqa: F401 — register tables on Base
from .api import courses, learn, topics
from .config import settings
from .content.loader import load_seed
from .db import Base, SessionLocal, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        load_seed(db)
    yield


app = FastAPI(title="Educator", lifespan=lifespan)
app.include_router(courses.router)
app.include_router(topics.router)
app.include_router(learn.router)


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
