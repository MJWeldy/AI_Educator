from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..content import llm_content
from ..content.worked_examples import normalize_worked_examples
from ..db import get_db
from ..llm.base import LLMError
from ..llm.ollama import OllamaProvider
from ..llm.router import get_setting
from ..models import Topic
from ..schemas import LessonOut, WorkedExample

router = APIRouter(prefix="/api/llm", tags=["llm"])


class LLMStatus(BaseModel):
    ollama_available: bool
    ollama_models: list[str]
    anthropic_key_set: bool
    default_provider: str
    ollama_model: str
    anthropic_model: str | None
    use_claude_for_ingestion: bool


@router.get("/status", response_model=LLMStatus)
async def status(db: Session = Depends(get_db)):
    models = await OllamaProvider().list_models()
    overrides = get_setting(db, "llm.overrides", {}) or {}
    return LLMStatus(
        ollama_available=bool(models),
        ollama_models=models,
        anthropic_key_set=bool(get_setting(db, "llm.anthropic_api_key")),
        default_provider=get_setting(db, "llm.default_provider", "ollama"),
        ollama_model=get_setting(db, "llm.ollama_model", "gpt-oss:20b"),
        anthropic_model=get_setting(db, "llm.anthropic_model", None),
        use_claude_for_ingestion=any(
            v.get("provider") == "anthropic" for v in overrides.values()
        ),
    )


@router.post("/topics/{topic_id}/lesson", response_model=LessonOut)
async def generate_lesson(topic_id: int, db: Session = Depends(get_db)):
    topic = db.get(Topic, topic_id)
    if topic is None:
        raise HTTPException(404, "topic not found")
    try:
        lesson = await llm_content.generate_lesson(db, topic)
    except LLMError as e:
        raise HTTPException(502, str(e))
    return LessonOut(
        content_md=lesson.content_md,
        worked_examples=[WorkedExample(**ex) for ex in normalize_worked_examples(lesson.worked_examples)],
        source=lesson.source,
    )


@router.post("/topics/{topic_id}/problems")
async def generate_problems(topic_id: int, db: Session = Depends(get_db)):
    """Generate a verified practice set for a topic with no generator."""
    from ..ingest.generate import PROBLEMS_SCHEMA, PROBLEMS_SYSTEM, verify_problem
    from ..llm import router as llm_router
    from ..llm.base import JobType, Message
    from ..llm.cache import cached_complete_json
    from ..models import Problem

    topic = db.get(Topic, topic_id)
    if topic is None:
        raise HTTPException(404, "topic not found")
    try:
        choice = llm_router.resolve(db, JobType.extra_problems)
        result = await cached_complete_json(
            db,
            choice,
            JobType.extra_problems,
            [
                Message("system", PROBLEMS_SYSTEM),
                Message(
                    "user",
                    f"Course: {topic.course.title}\nTopic: {topic.title}\nScope: {topic.description}",
                ),
            ],
            PROBLEMS_SCHEMA,
        )
    except LLMError as e:
        raise HTTPException(502, str(e))
    created = 0
    for pdoc in result.get("problems", []):
        parts = pdoc.get("parts", [])
        db.add(
            Problem(
                topic_id=topic.id,
                statement_md=pdoc["statement_md"],
                parts=parts,
                solution_md=pdoc.get("solution_md", ""),
                difficulty=max(1, min(3, int(pdoc.get("difficulty", 1)))),
                answer_verified=verify_problem(parts),
                source="llm",
                model=f"{choice.provider_name}:{choice.model}",
                review_status="approved",
            )
        )
        created += 1
    db.commit()
    return {"created": created}


class HintIn(BaseModel):
    statement_md: str
    parts: list[dict]
    wrong_answers: list[str] | None = None


@router.post("/hint")
async def hint(body: HintIn, db: Session = Depends(get_db)):
    try:
        stream = llm_content.hint_stream(db, body.statement_md, body.parts, body.wrong_answers)
    except LLMError as e:
        raise HTTPException(502, str(e))

    async def gen():
        try:
            async for piece in stream:
                yield piece
        except LLMError as e:
            yield f"\n\n_(hint unavailable: {e})_"

    return StreamingResponse(gen(), media_type="text/plain")


class ExplainIn(BaseModel):
    statement_md: str
    parts: list[dict]
    user_answers: list[str]
    canonical: list[str]


@router.post("/explain")
async def explain(body: ExplainIn, db: Session = Depends(get_db)):
    try:
        stream = llm_content.explain_stream(
            db, body.statement_md, body.parts, body.user_answers, body.canonical
        )
    except LLMError as e:
        raise HTTPException(502, str(e))

    async def gen():
        try:
            async for piece in stream:
                yield piece
        except LLMError as e:
            yield f"\n\n_(explanation unavailable: {e})_"

    return StreamingResponse(gen(), media_type="text/plain")
