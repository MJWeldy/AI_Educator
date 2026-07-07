"""Daily task queue: due reviews first, quizzes when triggered, then new
frontier lessons to fill the XP goal. Idempotent per calendar date."""

import random
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Mastery, Task, Topic, UserTopicState
from . import xp
from .graph import TopicGraph, effective_masteries, frontier

REVIEW_BATCH = 4  # topics per review task
REVIEW_XP = xp.REVIEW_XP
QUIZ_XP = xp.QUIZ_XP
QUIZ_EVERY_ACTIVE_DAYS = 4
QUIZ_MIN_POOL = 6
QUIZ_SIZE = 8
REVIEW_XP_SHARE = 0.5  # reviews fill at most half of the daily goal


def _review_problem(topic: Topic, rng: random.Random) -> dict | None:
    from ..content.generators import REGISTRY

    keys = [k for k in topic.generator_keys if k in REGISTRY]
    if not keys:
        return None
    return {
        "topic_id": topic.id,
        "generator_key": rng.choice(keys),
        "seed": rng.randrange(1, 2**31),
        "difficulty": 2,
        "done": False,
        "correct": None,
    }


def _due_states(db: Session, profile_id: int, now: datetime) -> list[UserTopicState]:
    states = db.scalars(
        select(UserTopicState).where(
            UserTopicState.profile_id == profile_id,
            UserTopicState.mastery.in_([Mastery.learned.value, Mastery.mastered.value]),
            UserTopicState.fsrs_due_at.is_not(None),
        )
    ).all()
    due = [s for s in states if s.fsrs_due_at and _as_utc(s.fsrs_due_at) <= now]
    due.sort(key=lambda s: _as_utc(s.fsrs_due_at))  # most overdue first
    return due


def _as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _quiz_due(db: Session, profile_id: int, today: str, learned_pool: int) -> bool:
    if learned_pool < QUIZ_MIN_POOL:
        return False
    last_quiz = db.scalar(
        select(Task)
        .where(Task.profile_id == profile_id, Task.type == "quiz")
        .order_by(Task.for_date.desc())
        .limit(1)
    )
    if last_quiz is None:
        return True
    active_days = db.scalars(
        select(Task.for_date)
        .where(Task.profile_id == profile_id, Task.for_date > last_quiz.for_date)
        .distinct()
    ).all()
    return len(active_days) >= QUIZ_EVERY_ACTIVE_DAYS


def build_today(db: Session, profile_id: int, now: datetime | None = None) -> list[Task]:
    now = now or datetime.now(timezone.utc)
    today = date.today().isoformat()

    existing = db.scalars(
        select(Task).where(Task.profile_id == profile_id, Task.for_date == today)
    ).all()
    if existing:
        return sorted(existing, key=lambda t: t.id)

    rng = random.Random()
    goal = xp.daily_goal(db)
    tasks: list[Task] = []
    budget = goal

    graph = TopicGraph.load(db)
    masteries = effective_masteries(db, graph, profile_id)

    # 1. Due reviews (capped at half the goal; overflow spills to tomorrow).
    review_budget = goal * REVIEW_XP_SHARE
    due = _due_states(db, profile_id, now)
    for i in range(0, len(due), REVIEW_BATCH):
        if review_budget < REVIEW_XP:
            break
        batch = due[i : i + REVIEW_BATCH]
        problems = []
        for s in batch:
            topic = graph.topics.get(s.topic_id)
            if topic is None:
                continue
            p = _review_problem(topic, rng)
            if p:
                problems.append(p)
        if not problems:
            continue
        tasks.append(
            Task(
                profile_id=profile_id,
                type="review",
                topic_ids=[p["topic_id"] for p in problems],
                for_date=today,
                payload={"problems": problems},
                xp_value=REVIEW_XP,
            )
        )
        review_budget -= REVIEW_XP
        budget -= REVIEW_XP

    # 2. Quiz when triggered: sample the learned/mastered pool, overdue-weighted.
    known_states = db.scalars(
        select(UserTopicState).where(
            UserTopicState.profile_id == profile_id,
            UserTopicState.mastery.in_([Mastery.learned.value, Mastery.mastered.value]),
        )
    ).all()
    if _quiz_due(db, profile_id, today, len(known_states)):
        def overdueness(s: UserTopicState) -> float:
            if not s.fsrs_due_at:
                return 0.0
            return (now - _as_utc(s.fsrs_due_at)).total_seconds()

        pool = sorted(known_states, key=overdueness, reverse=True)[: QUIZ_SIZE * 2]
        rng.shuffle(pool)
        chosen = pool[:QUIZ_SIZE]
        problems = []
        for s in chosen:
            topic = graph.topics.get(s.topic_id)
            if topic:
                p = _review_problem(topic, rng)
                if p:
                    problems.append(p)
        if problems:
            tasks.append(
                Task(
                    profile_id=profile_id,
                    type="quiz",
                    topic_ids=[p["topic_id"] for p in problems],
                    for_date=today,
                    payload={"problems": problems},
                    xp_value=QUIZ_XP,
                )
            )
            budget -= QUIZ_XP

    # 3. New lessons on the frontier fill what's left of the goal.
    course_order = {t.id: (t.course.sequence_order, t.depth_rank, -len(graph.dependents[t.id]))
                    for t in graph.topics.values()}
    ready = [tid for tid in frontier(graph, masteries)]
    ready.sort(key=lambda tid: course_order[tid])
    for tid in ready:
        if budget <= 0:
            break
        topic = graph.topics[tid]
        tasks.append(
            Task(
                profile_id=profile_id,
                type="lesson",
                topic_ids=[tid],
                for_date=today,
                payload={"title": topic.title},
                xp_value=topic.est_minutes,
            )
        )
        budget -= topic.est_minutes

    for t in tasks:
        db.add(t)
    db.commit()
    return sorted(tasks, key=lambda t: t.id)
