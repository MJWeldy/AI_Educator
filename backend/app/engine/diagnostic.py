"""Adaptive placement diagnostic: a calibrated frontier search over the DAG.

Every in-scope topic starts at P(known) = 0.5. Each probe picks the
median-depth topic among the uncertain ones (preferring well-connected hubs),
serves one problem, and propagates the result: a correct answer raises the
topic and its ancestors, a miss lowers the topic and its descendants.
The search stops when nothing is uncertain or the question budget runs out.
"""

import random
from collections import deque
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import DiagnosticSession, Mastery, Topic, UserTopicState
from . import srs
from .graph import TopicGraph

MAX_QUESTIONS = 25
UNCERTAIN_LO, UNCERTAIN_HI = 0.25, 0.75
KNOWN_P = 0.95
DECAY = 0.93
MASTER_THRESHOLD = 0.8


def start_session(db: Session, profile_id: int, course_slugs: list[str], graph: TopicGraph) -> DiagnosticSession:
    from ..models import Problem

    with_problems = set(
        db.scalars(select(Problem.topic_id).where(Problem.answer_verified.is_(True)))
    )
    scope_ids = [
        t.id
        for t in graph.topics.values()
        if t.course.slug in course_slugs and (t.generator_keys or t.id in with_problems)
    ]
    session = DiagnosticSession(
        profile_id=profile_id,
        course_scope=course_slugs,
        belief={str(tid): 0.5 for tid in scope_ids},
        asked=[],
    )
    db.add(session)
    db.commit()
    return session


def _distances(graph: TopicGraph, start: int, up: bool) -> dict[int, int]:
    """BFS distances to ancestors (up=True) or descendants."""
    dist = {start: 0}
    queue = deque([start])
    while queue:
        cur = queue.popleft()
        neighbors = graph.all_prereqs(cur) if up else graph.dependents[cur]
        for n in neighbors:
            if n not in dist:
                dist[n] = dist[cur] + 1
                queue.append(n)
    dist.pop(start)
    return dist


def next_probe(session: DiagnosticSession, graph: TopicGraph) -> int | None:
    if len(session.asked) >= MAX_QUESTIONS:
        return None
    asked_ids = {a["topic_id"] for a in session.asked}
    candidates = [
        int(tid)
        for tid, p in session.belief.items()
        if UNCERTAIN_LO < p < UNCERTAIN_HI and int(tid) not in asked_ids
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda tid: graph.topics[tid].depth_rank)
    median_depth = graph.topics[candidates[len(candidates) // 2]].depth_rank
    at_depth = [tid for tid in candidates if abs(graph.topics[tid].depth_rank - median_depth) <= 1]

    def degree(tid: int) -> int:
        return len(graph.dependents[tid]) + len(graph.all_prereqs(tid))

    return max(at_depth, key=degree)


def record_answer(
    db: Session, session: DiagnosticSession, graph: TopicGraph, topic_id: int, correct: bool
) -> None:
    belief = dict(session.belief)
    key = str(topic_id)
    if correct:
        belief[key] = KNOWN_P
        for aid, d in _distances(graph, topic_id, up=True).items():
            k = str(aid)
            if k in belief:
                belief[k] = max(belief[k], KNOWN_P * (DECAY**d))
    else:
        belief[key] = 1 - KNOWN_P
        for did, d in _distances(graph, topic_id, up=False).items():
            k = str(did)
            if k in belief:
                belief[k] = min(belief[k], 1 - KNOWN_P * (DECAY**d))
    session.belief = belief
    session.asked = list(session.asked) + [{"topic_id": topic_id, "correct": correct}]
    db.commit()


def finish(db: Session, session: DiagnosticSession, graph: TopicGraph) -> dict:
    """Apply placement: confident topics become mastered with synthetic FSRS
    cards whose due dates are jittered across three weeks, so old knowledge
    re-verifies itself gradually instead of flooding day one."""
    rng = random.Random(session.id)
    now = datetime.now(timezone.utc)
    placed = 0
    for tid_str, p in session.belief.items():
        if p < MASTER_THRESHOLD:
            continue
        tid = int(tid_str)
        state = db.get(UserTopicState, (session.profile_id, tid))
        if state is None:
            state = UserTopicState(profile_id=session.profile_id, topic_id=tid)
            db.add(state)
        elif state.mastery in (Mastery.learned.value, Mastery.mastered.value):
            continue  # never downgrade real progress
        state.mastery = Mastery.mastered.value
        state.placed_by_diagnostic = True
        srs.seed_from_diagnostic(
            state,
            stability_days=rng.uniform(15, 30),
            due=now + timedelta(days=rng.uniform(1, 21)),
        )
        placed += 1

    session.status = "finished"
    db.commit()

    # A wholly-missed placement means the learner lacks the prerequisites for
    # this course; point them at earlier material to start with.
    asked = list(session.asked)
    failed = bool(asked) and all(not a["correct"] for a in asked)
    suggested = _earlier_courses(session, graph) if failed else []
    return {
        "placed_mastered": placed,
        "questions_asked": len(asked),
        "failed_placement": failed,
        "suggested_earlier": suggested,
    }


def _earlier_courses(session: DiagnosticSession, graph: TopicGraph) -> list[dict]:
    """Courses to study before the placed-into one: those holding prerequisites
    of the scoped topics, else any course earlier in the curriculum sequence."""
    scope = set(session.course_scope)
    scoped_tids = [int(t) for t in session.belief if int(t) in graph.topics]

    prereq: dict[str, tuple[int, str]] = {}
    for tid in scoped_tids:
        for pid in graph.all_prereqs(tid):
            course = graph.topics[pid].course
            if course.slug not in scope:
                prereq[course.slug] = (course.sequence_order, course.title)
    if not prereq:
        scoped_order = min(
            (graph.topics[tid].course.sequence_order for tid in scoped_tids), default=0
        )
        for t in graph.topics.values():
            course = t.course
            if course.slug not in scope and course.sequence_order < scoped_order:
                prereq[course.slug] = (course.sequence_order, course.title)

    ordered = sorted(prereq.items(), key=lambda kv: kv[1][0], reverse=True)  # nearest first
    return [{"slug": slug, "title": title} for slug, (_seq, title) in ordered[:3]]
