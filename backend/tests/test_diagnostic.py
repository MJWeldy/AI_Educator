"""Simulated-student oracle: a student who knows everything up to depth K
should be placed near depth K by the adaptive diagnostic."""

from sqlalchemy import select

from app.engine import diagnostic as diag
from app.engine.graph import TopicGraph, effective_masteries
from app.models import Topic, UserTopicState


def run_diagnostic(db, oracle_knows) -> dict:
    graph = TopicGraph.load(db)
    session = diag.start_session(db, 1, ["foundations-i"], graph)
    while True:
        tid = diag.next_probe(session, graph)
        if tid is None:
            break
        diag.record_answer(db, session, graph, tid, oracle_knows(graph.topics[tid]))
    return diag.finish(db, session, graph)


def test_student_knows_nothing(seeded_db):
    result = run_diagnostic(seeded_db, lambda t: False)
    assert result["placed_mastered"] == 0
    assert result["questions_asked"] <= diag.MAX_QUESTIONS


def test_student_knows_everything(seeded_db):
    result = run_diagnostic(seeded_db, lambda t: True)
    topics = seeded_db.scalars(select(Topic)).all()
    # Almost the whole graph should be placed as mastered.
    assert result["placed_mastered"] >= len(topics) * 0.8


def test_partial_knowledge_places_near_boundary(seeded_db):
    K = 4  # knows everything shallower than depth 4
    result = run_diagnostic(seeded_db, lambda t: t.depth_rank < K)
    assert result["questions_asked"] <= diag.MAX_QUESTIONS

    graph = TopicGraph.load(seeded_db)
    placed = {
        s.topic_id
        for s in seeded_db.scalars(
            select(UserTopicState).where(UserTopicState.placed_by_diagnostic.is_(True))
        )
    }
    # Nothing the student doesn't know (beyond one level of slack) is mastered.
    for tid in placed:
        assert graph.topics[tid].depth_rank <= K, (
            f"{graph.topics[tid].slug} (depth {graph.topics[tid].depth_rank}) "
            f"wrongly placed for boundary {K}"
        )
    # A decent share of genuinely-known topics got credit.
    known = [t for t in graph.topics.values() if t.depth_rank < K - 1]
    credited = [t for t in known if t.id in placed]
    assert len(credited) >= len(known) * 0.5

    # The learning frontier lands within ±1 of the boundary.
    masteries = effective_masteries(seeded_db, graph, 1)
    frontier_depths = [
        graph.topics[tid].depth_rank
        for tid, m in masteries.items()
        if m == "unlocked" and graph.topics[tid].depth_rank > 0
    ]
    assert frontier_depths, "diagnostic should open a frontier"
    assert min(frontier_depths) >= K - 1


def test_diagnostic_never_downgrades_real_progress(seeded_db):
    from app.engine.mastery import get_or_create_state
    from app.models import Mastery

    topic = seeded_db.scalar(select(Topic).where(Topic.slug == "place-value"))
    state = get_or_create_state(seeded_db, 1, topic.id)
    state.mastery = Mastery.learned.value
    seeded_db.flush()

    run_diagnostic(seeded_db, lambda t: False)
    seeded_db.refresh(state)
    assert state.mastery == Mastery.learned.value
