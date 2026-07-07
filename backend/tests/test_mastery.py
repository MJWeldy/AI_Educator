from app.engine.mastery import get_or_create_state, record_lesson_attempt
from app.models import Mastery


def make_state(db):
    from app.models import Course, Profile, Topic

    db.add(Course(id=1, slug="c", title="c"))
    db.add(Profile(id=1, name="t"))
    db.add(Topic(id=1, slug="t1", course_id=1, title="t1"))
    db.flush()
    return get_or_create_state(db, 1, 1)


def test_lesson_completes_after_three_tiers(db):
    state = make_state(db)
    assert state.mastery == Mastery.learning.value
    completed = False
    for _ in range(6):  # 2 correct per tier × 3 tiers
        events = record_lesson_attempt(state, True)
        if events["lesson_complete"]:
            completed = True
    assert completed
    assert state.mastery == Mastery.learned.value


def test_wrong_answers_reset_streak(db):
    state = make_state(db)
    record_lesson_attempt(state, True)
    record_lesson_attempt(state, False)  # streak resets
    assert state.lesson_progress["streak"] == 0
    assert state.lesson_progress["tier"] == 1
    events = record_lesson_attempt(state, True)
    assert not events["tier_advanced"]
    events = record_lesson_attempt(state, True)
    assert events["tier_advanced"]
    assert state.lesson_progress["tier"] == 2


def test_three_misses_reshow_examples(db):
    state = make_state(db)
    record_lesson_attempt(state, False)
    record_lesson_attempt(state, False)
    events = record_lesson_attempt(state, False)
    assert events["show_examples"]
    assert state.lesson_progress["misses"] == 0  # reset after re-teach


def test_fsrs_init_on_completion(db):
    from app.engine.srs import init_card

    state = make_state(db)
    init_card(state)
    assert state.fsrs_card is not None
    assert state.fsrs_due_at is not None
    assert state.fsrs_stability is not None
