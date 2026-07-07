import random

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..content import checking
from ..content.serving import pick_problem, resolve_submission
from ..db import get_db
from .deps import current_profile_id
from ..engine import diagnostic as diag
from ..engine.graph import TopicGraph
from ..models import Attempt, DiagnosticSession, Topic

router = APIRouter(prefix="/api/diagnostic", tags=["diagnostic"])


class ProbeOut(BaseModel):
    topic_id: int
    topic_title: str
    problem_id: int | None = None
    generator_key: str | None = None
    seed: int | None = None
    difficulty: int
    statement_md: str
    parts: list[dict]


class SessionOut(BaseModel):
    session_id: int
    status: str
    asked_count: int
    max_questions: int
    probe: ProbeOut | None


def _make_probe(db: Session, topic_id: int) -> ProbeOut | None:
    topic = db.get(Topic, topic_id)
    served = pick_problem(db, topic, 2, verified_only=True)
    if served is None:
        return None
    return ProbeOut(
        topic_id=topic.id,
        topic_title=topic.title,
        problem_id=served.problem_id,
        generator_key=served.generator_key,
        seed=served.seed,
        difficulty=served.difficulty,
        statement_md=served.statement_md,
        parts=served.parts_public,
    )


def _session_out(db: Session, session: DiagnosticSession, graph: TopicGraph) -> SessionOut:
    probe = None
    if session.status == "active":
        tid = diag.next_probe(session, graph)
        if tid is not None:
            probe = _make_probe(db, tid)
    return SessionOut(
        session_id=session.id,
        status=session.status,
        asked_count=len(session.asked),
        max_questions=diag.MAX_QUESTIONS,
        probe=probe,
    )


class StartIn(BaseModel):
    course_slugs: list[str]


@router.post("/start", response_model=SessionOut)
def start(
    body: StartIn,
    db: Session = Depends(get_db),
    profile_id: int = Depends(current_profile_id),
):
    graph = TopicGraph.load(db)
    session = diag.start_session(db, profile_id, body.course_slugs, graph)
    if not session.belief:
        raise HTTPException(400, "no probeable topics in the chosen courses")
    return _session_out(db, session, graph)


class AnswerIn(BaseModel):
    topic_id: int
    problem_id: int | None = None
    generator_key: str | None = None
    seed: int | None = None
    difficulty: int = 2
    answers: list[str]


class AnswerOut(BaseModel):
    correct: bool
    part_results: list[dict]
    session: SessionOut


@router.post("/{session_id}/answer", response_model=AnswerOut)
def answer(
    session_id: int,
    body: AnswerIn,
    db: Session = Depends(get_db),
    profile_id: int = Depends(current_profile_id),
):
    session = db.get(DiagnosticSession, session_id)
    if session is None or session.status != "active":
        raise HTTPException(404, "no active session")
    graph = TopicGraph.load(db)

    try:
        parts, presented, _solution = resolve_submission(
            db,
            problem_id=body.problem_id,
            generator_key=body.generator_key,
            seed=body.seed,
            difficulty=body.difficulty,
        )
    except KeyError as e:
        raise HTTPException(400, str(e))
    correct, part_results = checking.check_instance(parts, body.answers)
    db.add(
        Attempt(
            profile_id=profile_id,
            topic_id=body.topic_id,
            problem_id=body.problem_id,
            generator_key=body.generator_key,
            seed=body.seed,
            difficulty=body.difficulty,
            presented=presented,
            user_answer={"answers": body.answers},
            correct=correct,
            part_results=part_results,
            context="diagnostic",
        )
    )
    diag.record_answer(db, session, graph, body.topic_id, correct)
    return AnswerOut(correct=correct, part_results=part_results, session=_session_out(db, session, graph))


class FinishOut(BaseModel):
    placed_mastered: int
    questions_asked: int


@router.post("/{session_id}/finish", response_model=FinishOut)
def finish(session_id: int, db: Session = Depends(get_db)):
    session = db.get(DiagnosticSession, session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    if session.status != "active":
        raise HTTPException(409, "session already finished")
    graph = TopicGraph.load(db)
    result = diag.finish(db, session, graph)
    return FinishOut(**result)
