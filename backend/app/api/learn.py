from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..content import checking
from ..content.serving import pick_problem, resolve_submission
from ..content.worked_examples import normalize_worked_examples
from ..db import get_db
from .deps import current_profile_id
from ..engine import xp
from ..engine.graph import TopicGraph, effective_masteries
from ..engine.mastery import fresh_progress, get_or_create_state, record_lesson_attempt
from ..engine.srs import init_card
from ..models import Attempt, Lesson, Mastery, Topic, UserTopicState
from ..schemas import LessonOut, WorkedExample

router = APIRouter(prefix="/api/learn", tags=["learn"])


class ProblemOut(BaseModel):
    problem_id: int | None = None
    generator_key: str | None = None
    seed: int | None = None
    difficulty: int
    statement_md: str
    parts: list[dict]


class LearnState(BaseModel):
    topic_id: int
    topic_title: str
    course_slug: str
    mastery: str
    progress: dict
    lesson: LessonOut | None
    problem: ProblemOut | None


class AttemptIn(BaseModel):
    problem_id: int | None = None
    generator_key: str | None = None
    seed: int | None = None
    difficulty: int = 1
    answers: list[str]
    time_ms: int | None = None
    hints_used: int = 0


class AttemptOut(BaseModel):
    correct: bool
    part_results: list[dict]
    solution_md: str
    canonical: list[str]
    events: dict
    progress: dict
    mastery: str
    xp_awarded: int
    next_problem: ProblemOut | None


def _next_problem(db: Session, topic: Topic, progress: dict) -> ProblemOut | None:
    served = pick_problem(db, topic, int(progress.get("tier", 1)))
    if served is None:
        return None
    return ProblemOut(
        problem_id=served.problem_id,
        generator_key=served.generator_key,
        seed=served.seed,
        difficulty=served.difficulty,
        statement_md=served.statement_md,
        parts=served.parts_public,
    )


def _lesson_out(db: Session, topic_id: int) -> LessonOut | None:
    lesson = db.scalar(
        select(Lesson)
        .where(Lesson.topic_id == topic_id, Lesson.review_status == "approved")
        .order_by(Lesson.position)
    )
    if lesson is None:
        return None
    return LessonOut(
        content_md=lesson.content_md,
        worked_examples=[WorkedExample(**ex) for ex in normalize_worked_examples(lesson.worked_examples)],
        source=lesson.source,
    )


@router.get("/{topic_id}", response_model=LearnState)
def learn_state(
    topic_id: int,
    db: Session = Depends(get_db),
    profile_id: int = Depends(current_profile_id),
):
    topic = db.get(Topic, topic_id)
    if topic is None:
        raise HTTPException(404, "topic not found")
    graph = TopicGraph.load(db)
    masteries = effective_masteries(db, graph, profile_id)
    mastery = masteries.get(topic_id, Mastery.locked.value)
    if mastery == Mastery.locked.value:
        raise HTTPException(409, "topic is locked — finish its prerequisites first")

    state = db.get(UserTopicState, (profile_id, topic_id))
    progress = (state.lesson_progress if state else None) or fresh_progress()

    return LearnState(
        topic_id=topic.id,
        topic_title=topic.title,
        course_slug=topic.course.slug,
        mastery=mastery,
        progress=progress,
        lesson=_lesson_out(db, topic_id),
        problem=_next_problem(db, topic, progress),
    )


@router.post("/{topic_id}/attempt", response_model=AttemptOut)
def submit_attempt(
    topic_id: int,
    body: AttemptIn,
    db: Session = Depends(get_db),
    profile_id: int = Depends(current_profile_id),
):
    topic = db.get(Topic, topic_id)
    if topic is None:
        raise HTTPException(404, "topic not found")
    try:
        parts, presented, solution_md = resolve_submission(
            db,
            problem_id=body.problem_id,
            generator_key=body.generator_key,
            seed=body.seed,
            difficulty=body.difficulty,
        )
    except KeyError as e:
        raise HTTPException(400, str(e))
    correct, part_results = checking.check_instance(parts, body.answers)

    state = get_or_create_state(db, profile_id, topic_id)
    was_learning = state.mastery == Mastery.learning.value
    events = (
        record_lesson_attempt(state, correct)
        if was_learning
        else {"tier_advanced": False, "lesson_complete": False, "show_examples": False}
    )

    db.add(
        Attempt(
            profile_id=profile_id,
            topic_id=topic_id,
            problem_id=body.problem_id,
            generator_key=body.generator_key,
            seed=body.seed,
            difficulty=body.difficulty,
            presented=presented,
            user_answer={"answers": body.answers},
            correct=correct,
            part_results=part_results,
            hints_used=body.hints_used,
            time_ms=body.time_ms,
            context="lesson",
        )
    )

    xp_awarded = 0
    if events["lesson_complete"]:
        xp_awarded = topic.est_minutes
        xp.award(db, profile_id, xp_awarded, f"lesson:{topic.slug}")
        init_card(state)

    db.commit()

    next_problem = None if events["lesson_complete"] else _next_problem(db, topic, state.lesson_progress)
    return AttemptOut(
        correct=correct,
        part_results=part_results,
        solution_md=solution_md,
        canonical=[str(p["canonical"]) for p in parts],
        events=events,
        progress=state.lesson_progress,
        mastery=state.mastery,
        xp_awarded=xp_awarded,
        next_problem=next_problem,
    )


@router.get("/preview/expression")
def preview_expression(expr: str):
    latex = checking.preview_latex(expr)
    return {"ok": latex is not None, "latex": latex}
