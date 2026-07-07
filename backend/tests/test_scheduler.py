from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.engine import scheduler
from app.engine.mastery import get_or_create_state
from app.engine.srs import init_card
from app.models import Mastery, Task, Topic, UserTopicState


def learn_topic(db, slug: str, due_days_ago: float | None = None):
    topic = db.scalar(select(Topic).where(Topic.slug == slug))
    state = get_or_create_state(db, 1, topic.id)
    state.mastery = Mastery.learned.value
    init_card(state)
    if due_days_ago is not None:
        state.fsrs_due_at = datetime.now(timezone.utc) - timedelta(days=due_days_ago)
    db.flush()
    return topic


def test_first_day_queue_is_frontier_lessons(seeded_db):
    tasks = scheduler.build_today(seeded_db, 1)
    assert tasks, "queue should not be empty"
    assert all(t.type == "lesson" for t in tasks)
    # The only frontier topic at the start is place-value.
    first = seeded_db.get(Topic, tasks[0].topic_ids[0])
    assert first.slug == "place-value"


def test_queue_idempotent_per_day(seeded_db):
    a = scheduler.build_today(seeded_db, 1)
    b = scheduler.build_today(seeded_db, 1)
    assert [t.id for t in a] == [t.id for t in b]


def test_due_reviews_come_first(seeded_db):
    learn_topic(seeded_db, "place-value", due_days_ago=2)
    learn_topic(seeded_db, "whole-add-sub", due_days_ago=1)
    tasks = scheduler.build_today(seeded_db, 1)
    assert tasks[0].type == "review"
    reviewed = set(tasks[0].topic_ids)
    assert {t.id for t in seeded_db.scalars(select(Topic).where(Topic.slug.in_(["place-value", "whole-add-sub"])))} <= reviewed
    # Review problems carry generator seeds ready to serve.
    for p in tasks[0].payload["problems"]:
        assert p["generator_key"] and p["seed"] > 0


def test_no_review_when_nothing_due(seeded_db):
    learn_topic(seeded_db, "place-value")  # due tomorrow-ish, not today
    state = seeded_db.get(UserTopicState, (1, seeded_db.scalar(select(Topic).where(Topic.slug == "place-value")).id))
    state.fsrs_due_at = datetime.now(timezone.utc) + timedelta(days=3)
    seeded_db.flush()
    tasks = scheduler.build_today(seeded_db, 1)
    assert all(t.type != "review" for t in tasks)


def test_quiz_triggers_with_enough_learned_topics(seeded_db):
    slugs = [
        "place-value", "whole-add-sub", "whole-multiply", "whole-divide",
        "rounding-estimation", "order-of-operations", "negative-numbers",
    ]
    for s in slugs:
        learn_topic(seeded_db, s)
    tasks = scheduler.build_today(seeded_db, 1)
    assert any(t.type == "quiz" for t in tasks), "first quiz should trigger with a big enough pool"


def test_lessons_fill_to_goal(seeded_db):
    tasks = scheduler.build_today(seeded_db, 1)
    lesson_xp = sum(t.xp_value for t in tasks if t.type == "lesson")
    # The frontier only has one topic at the very start, so the queue may be
    # smaller than the goal — but it must never be empty and never wildly over.
    assert 0 < lesson_xp <= 60


def test_srs_review_flow(seeded_db):
    from fsrs import Rating

    from app.engine import srs

    topic = learn_topic(seeded_db, "place-value", due_days_ago=1)
    state = seeded_db.get(UserTopicState, (1, topic.id))
    before_due = state.fsrs_due_at
    srs.review(state, Rating.Good)
    assert state.fsrs_due_at > before_due
    assert state.reps == 1

    srs.review(state, Rating.Again)
    assert state.lapses == 1


def test_mastery_promotion(seeded_db):
    from fsrs import Rating

    from app.engine import srs

    topic = learn_topic(seeded_db, "place-value")
    state = seeded_db.get(UserTopicState, (1, topic.id))
    now = datetime.now(timezone.utc)
    # Simulate spaced successful reviews far apart until stability crosses the bar.
    for i in range(1, 8):
        srs.review(state, Rating.Good, now=now + timedelta(days=7 * i))
    assert state.mastery == Mastery.mastered.value

    # A lapse demotes back to learned.
    srs.review(state, Rating.Again, now=now + timedelta(days=60))
    assert state.mastery == Mastery.learned.value
