"""Spaced repetition via py-fsrs: one card per topic.

Ratings are derived from review outcomes rather than self-report:
wrong → Again, correct-with-hints/slow → Hard, correct → Good, fast+clean → Easy.
"""

from datetime import datetime, timezone

from fsrs import Card, Rating, Scheduler

from ..models import Mastery, UserTopicState

MASTERY_STABILITY_DAYS = 21.0
MASTERY_MIN_REPS = 3

_scheduler = Scheduler(enable_fuzzing=True)


def _apply(state: UserTopicState, card: Card) -> None:
    state.fsrs_card = card.to_dict()
    state.fsrs_due_at = card.due
    state.fsrs_stability = card.stability


def init_card(state: UserTopicState, now: datetime | None = None) -> None:
    """Called when a lesson completes: schedule the first review ~1 day out."""
    now = now or datetime.now(timezone.utc)
    card, _ = _scheduler.review_card(Card(), Rating.Good, review_datetime=now)
    _apply(state, card)
    state.reps = 0


def derive_rating(correct: bool, hints_used: int, slow: bool) -> Rating:
    if not correct:
        return Rating.Again
    if hints_used > 0 or slow:
        return Rating.Hard
    return Rating.Good


def review(state: UserTopicState, rating: Rating, now: datetime | None = None) -> None:
    now = now or datetime.now(timezone.utc)
    card = Card.from_dict(state.fsrs_card) if state.fsrs_card else Card()
    card, _ = _scheduler.review_card(card, rating, review_datetime=now)
    _apply(state, card)

    if rating == Rating.Again:
        state.lapses += 1
        if state.mastery == Mastery.mastered.value:
            state.mastery = Mastery.learned.value
    else:
        state.reps += 1
        if (
            state.mastery == Mastery.learned.value
            and (card.stability or 0) >= MASTERY_STABILITY_DAYS
            and state.reps >= MASTERY_MIN_REPS
        ):
            state.mastery = Mastery.mastered.value


def seed_from_diagnostic(
    state: UserTopicState, stability_days: float, due: datetime
) -> None:
    """Diagnostic-placed topics get a synthetic card with jittered due dates."""
    card = Card()
    card.stability = stability_days
    card.difficulty = 5.0
    card.due = due
    _apply(state, card)
    state.reps = 1
