from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..llm.base import JobType
from ..llm.router import INGEST_JOBS, get_setting, set_setting

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsOut(BaseModel):
    daily_xp_goal: int
    default_provider: str
    ollama_model: str
    anthropic_key_set: bool
    anthropic_model: str | None
    use_claude_for_ingestion: bool


class SettingsIn(BaseModel):
    daily_xp_goal: int | None = None
    default_provider: str | None = None
    ollama_model: str | None = None
    anthropic_api_key: str | None = None  # empty string clears the key
    anthropic_model: str | None = None
    use_claude_for_ingestion: bool | None = None


def _current(db: Session) -> SettingsOut:
    overrides = get_setting(db, "llm.overrides", {}) or {}
    return SettingsOut(
        daily_xp_goal=get_setting(db, "goal.daily_xp", 30),
        default_provider=get_setting(db, "llm.default_provider", "ollama"),
        ollama_model=get_setting(db, "llm.ollama_model", "gpt-oss:20b"),
        anthropic_key_set=bool(get_setting(db, "llm.anthropic_api_key")),
        anthropic_model=get_setting(db, "llm.anthropic_model", None),
        use_claude_for_ingestion=any(v.get("provider") == "anthropic" for v in overrides.values()),
    )


@router.get("", response_model=SettingsOut)
def read(db: Session = Depends(get_db)):
    return _current(db)


@router.put("", response_model=SettingsOut)
def update(body: SettingsIn, db: Session = Depends(get_db)):
    if body.daily_xp_goal is not None and body.daily_xp_goal > 0:
        set_setting(db, "goal.daily_xp", body.daily_xp_goal)
    if body.default_provider in ("ollama", "anthropic"):
        set_setting(db, "llm.default_provider", body.default_provider)
    if body.ollama_model:
        set_setting(db, "llm.ollama_model", body.ollama_model)
    if body.anthropic_api_key is not None:
        set_setting(db, "llm.anthropic_api_key", body.anthropic_api_key or None)
    if body.anthropic_model:
        set_setting(db, "llm.anthropic_model", body.anthropic_model)
    if body.use_claude_for_ingestion is not None:
        overrides = dict(get_setting(db, "llm.overrides", {}) or {})
        if body.use_claude_for_ingestion:
            for job in INGEST_JOBS | {JobType.lesson_text}:
                overrides[job.value] = {"provider": "anthropic"}
        else:
            overrides = {
                k: v for k, v in overrides.items() if v.get("provider") != "anthropic"
            }
        set_setting(db, "llm.overrides", overrides)
    db.commit()
    return _current(db)
