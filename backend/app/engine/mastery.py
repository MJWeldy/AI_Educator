"""Lesson progression: scaffolded practice in 3 difficulty tiers.

A tier is passed after ADVANCE_STREAK consecutive correct answers; passing
tier 3 completes the lesson and the topic becomes `learned`. Three misses at
one tier re-surfaces the worked examples (and, later, an LLM hint).
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..models import Mastery, UserTopicState

TIERS = 3
ADVANCE_STREAK = 2
MISS_LIMIT = 3


def fresh_progress() -> dict:
    return {"tier": 1, "streak": 0, "misses": 0, "done": 0}


def get_or_create_state(db: Session, profile_id: int, topic_id: int) -> UserTopicState:
    state = db.get(UserTopicState, (profile_id, topic_id))
    if state is None:
        state = UserTopicState(
            profile_id=profile_id,
            topic_id=topic_id,
            mastery=Mastery.learning.value,
            lesson_progress=fresh_progress(),
        )
        db.add(state)
        db.flush()
    return state


def record_lesson_attempt(state: UserTopicState, correct: bool) -> dict:
    """Advance the lesson state machine. Returns events for the UI."""
    progress = dict(state.lesson_progress or fresh_progress())
    events = {"tier_advanced": False, "lesson_complete": False, "show_examples": False}

    progress["done"] += 1
    if correct:
        progress["streak"] += 1
        progress["misses"] = 0
        if progress["streak"] >= ADVANCE_STREAK:
            if progress["tier"] >= TIERS:
                events["lesson_complete"] = True
                state.mastery = Mastery.learned.value
            else:
                progress["tier"] += 1
                events["tier_advanced"] = True
            progress["streak"] = 0
    else:
        progress["streak"] = 0
        progress["misses"] += 1
        if progress["misses"] >= MISS_LIMIT:
            events["show_examples"] = True
            progress["misses"] = 0

    state.lesson_progress = progress
    state.updated_at = datetime.now(timezone.utc)
    return events
