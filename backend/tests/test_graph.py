import pytest

from app.engine.graph import CycleError, TopicGraph, effective_masteries, frontier
from app.models import Mastery, Topic, TopicEdge, UserTopicState


def make_topic(id: int, slug: str) -> Topic:
    return Topic(id=id, slug=slug, course_id=1, title=slug)


def edge(prereq: int, topic: int, kind: str = "hard") -> TopicEdge:
    return TopicEdge(prereq_id=prereq, topic_id=topic, kind=kind)


def chain_graph() -> TopicGraph:
    # 1 -> 2 -> 3, and 1 -> 4 (soft)
    topics = [make_topic(i, f"t{i}") for i in range(1, 5)]
    return TopicGraph(topics, [edge(1, 2), edge(2, 3), edge(1, 4, "soft")])


def test_topological_order_respects_edges():
    g = chain_graph()
    order = g.topological_order()
    assert order.index(1) < order.index(2) < order.index(3)
    assert order.index(1) < order.index(4)


def test_cycle_detection():
    topics = [make_topic(1, "a"), make_topic(2, "b")]
    g = TopicGraph(topics, [edge(1, 2), edge(2, 1)])
    with pytest.raises(CycleError):
        g.topological_order()


def test_depth_ranks():
    g = chain_graph()
    ranks = g.depth_ranks()
    assert ranks == {1: 0, 2: 1, 3: 2, 4: 1}


def test_ancestors_descendants():
    g = chain_graph()
    assert g.ancestors(3) == {1, 2}
    assert g.descendants(1) == {2, 3, 4}


def test_unlock_logic(db):
    from app.models import Course, Profile

    db.add(Course(id=1, slug="c", title="c"))
    db.add(Profile(id=1, name="t"))
    for t in [make_topic(i, f"t{i}") for i in range(1, 4)]:
        db.add(t)
    db.add(edge(1, 2))
    db.add(edge(2, 3))
    db.flush()

    g = TopicGraph.load(db)
    m = effective_masteries(db, g, 1)
    # Root unlocked, everything downstream locked.
    assert m == {1: "unlocked", 2: "locked", 3: "locked"}
    assert frontier(g, m) == [1]

    # Learning topic 1 doesn't unlock topic 2 yet.
    db.add(UserTopicState(profile_id=1, topic_id=1, mastery=Mastery.learning.value))
    db.flush()
    m = effective_masteries(db, g, 1)
    assert m[1] == "learning" and m[2] == "locked"

    # Learned topic 1 unlocks topic 2 but not 3.
    db.query(UserTopicState).filter_by(topic_id=1).update({"mastery": Mastery.learned.value})
    db.flush()
    m = effective_masteries(db, g, 1)
    assert m == {1: "learned", 2: "unlocked", 3: "locked"}
    assert frontier(g, m) == [2]
