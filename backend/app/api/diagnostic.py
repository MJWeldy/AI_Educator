import random

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..content import checking
from ..content.generators import REGISTRY, make_instance
from ..db import get_db
from ..engine import diagnostic as diag
from ..engine.graph import TopicGraph
from ..models import Attempt, DiagnosticSession, Topic

router = APIRouter(prefix="/api/diagnostic", tags=["diagnostic"])

PROFILE_ID = 1


class ProbeOut(BaseModel):
    topic_id: int
    topic_title: str
    generator_key: str
    seed: int
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
    keys = [k for k in (topic.generator_keys or []) if k in REGISTRY]
    if not keys:
        return None
    rng = random.Random()
    key = rng.choice(keys)
    seed = rng.randrange(1, 2**31)
    inst = make_instance(key, seed, 2)
    pub = inst.public_dict()
    return ProbeOut(
        topic_id=topic.id,
        topic_title=topic.title,
        generator_key=key,
        seed=seed,
        difficulty=2,
        statement_md=pub["statement_md"],
        parts=pub["parts"],
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
def start(body: StartIn, db: Session = Depends(get_db)):
    graph = TopicGraph.load(db)
    session = diag.start_session(db, PROFILE_ID, body.course_slugs, graph)
    if not session.belief:
        raise HTTPException(400, "no probeable topics in the chosen courses")
    return _session_out(db, session, graph)


class AnswerIn(BaseModel):
    topic_id: int
    generator_key: str
    seed: int
    difficulty: int
    answers: list[str]


class AnswerOut(BaseModel):
    correct: bool
    part_results: list[dict]
    session: SessionOut


@router.post("/{session_id}/answer", response_model=AnswerOut)
def answer(session_id: int, body: AnswerIn, db: Session = Depends(get_db)):
    session = db.get(DiagnosticSession, session_id)
    if session is None or session.status != "active":
        raise HTTPException(404, "no active session")
    graph = TopicGraph.load(db)

    inst = make_instance(body.generator_key, body.seed, body.difficulty)
    parts = [
        {
            "prompt_md": p.prompt_md,
            "answer_type": p.answer_type,
            "canonical": p.canonical,
            "tolerance": p.tolerance,
            "choices": p.choices,
        }
        for p in inst.parts
    ]
    correct, part_results = checking.check_instance(parts, body.answers)
    db.add(
        Attempt(
            profile_id=PROFILE_ID,
            topic_id=body.topic_id,
            generator_key=body.generator_key,
            seed=body.seed,
            difficulty=body.difficulty,
            presented=inst.to_dict(),
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
