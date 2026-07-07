from sqlalchemy import select

from app.content.loader import load_seed
from app.models import Course, Lesson, Resource, Topic, TopicEdge


def test_seed_loads(seeded_db):
    db = seeded_db
    courses = db.scalars(select(Course)).all()
    assert any(c.slug == "foundations-i" for c in courses)
    topics = db.scalars(select(Topic)).all()
    assert len(topics) >= 40
    assert db.scalars(select(TopicEdge)).all(), "seed should define prerequisite edges"
    assert db.scalars(select(Lesson)).all(), "seed should include hand-written lessons"
    assert db.scalars(select(Resource)).all(), "seed should include external resources"


def test_depth_ranks_assigned(seeded_db):
    db = seeded_db
    root = db.scalar(select(Topic).where(Topic.slug == "em-counting"))
    place_value = db.scalar(select(Topic).where(Topic.slug == "place-value"))
    two_step = db.scalar(select(Topic).where(Topic.slug == "two-step-equations"))
    assert root.depth_rank == 0
    assert place_value.depth_rank > root.depth_rank
    assert two_step.depth_rank > place_value.depth_rank


def test_loader_is_idempotent(seeded_db):
    db = seeded_db
    before = {
        "topics": db.scalars(select(Topic)).all().__len__(),
        "edges": db.scalars(select(TopicEdge)).all().__len__(),
        "lessons": db.scalars(select(Lesson)).all().__len__(),
        "resources": db.scalars(select(Resource)).all().__len__(),
    }
    load_seed(db)  # run again
    after = {
        "topics": db.scalars(select(Topic)).all().__len__(),
        "edges": db.scalars(select(TopicEdge)).all().__len__(),
        "lessons": db.scalars(select(Lesson)).all().__len__(),
        "resources": db.scalars(select(Resource)).all().__len__(),
    }
    assert before == after


def test_every_generator_key_unique_per_topic(seeded_db):
    db = seeded_db
    for topic in db.scalars(select(Topic)):
        keys = topic.generator_keys
        assert len(keys) == len(set(keys))
