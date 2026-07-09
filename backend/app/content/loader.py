"""Idempotent seed curriculum sync: YAML files in content/seed/ -> DB.

Each YAML file is one course:

    slug: foundations-i
    title: Mathematical Foundations I
    description: ...
    sequence_order: 10
    units:
      - title: Fractions
        topics:
          - slug: fractions-add-like
            title: Adding fractions with like denominators
            est_minutes: 10
            generators: [fractions.add_like]
            prereqs: [other-topic-slug]        # hard edges
            soft_prereqs: [another-slug]
            lesson: |
              markdown with $LaTeX$
            worked_examples:
              - problem: ...
                solution: ...
            resources:
              - {kind: video, title: ..., url: ...}

Upserts by slug; prunes seed-sourced edges/resources no longer present;
recomputes depth_rank. Safe to run at every startup.
"""

from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import SEED_DIR
from ..engine.graph import TopicGraph
from ..models import Course, Lesson, Profile, Resource, Topic, TopicEdge


def load_seed(db: Session, seed_dir: Path = SEED_DIR) -> dict:
    if db.get(Profile, 1) is None:
        db.add(Profile(id=1, name="Learner"))

    course_docs = []
    for path in sorted(seed_dir.glob("*.yaml")):
        with open(path) as f:
            course_docs.append(yaml.safe_load(f))

    topics_by_slug: dict[str, Topic] = {
        t.slug: t for t in db.scalars(select(Topic).where(Topic.source == "seed"))
    }
    stats = {"courses": 0, "topics": 0, "edges": 0, "lessons": 0, "resources": 0}
    pending_edges: list[tuple[str, str, str]] = []  # (prereq_slug, topic_slug, kind)

    for doc in course_docs:
        course = db.scalar(select(Course).where(Course.slug == doc["slug"]))
        if course is None:
            course = Course(slug=doc["slug"], source="seed")
            db.add(course)
        course.title = doc["title"]
        course.description = doc.get("description", "")
        course.level = doc.get("level", "")
        course.category = doc.get("category", "Mathematics")
        course.sequence_order = doc.get("sequence_order", 0)
        db.flush()
        stats["courses"] += 1

        for unit in doc.get("units", []):
            for tdoc in unit.get("topics", []):
                topic = topics_by_slug.get(tdoc["slug"])
                if topic is None:
                    topic = Topic(slug=tdoc["slug"], source="seed", course_id=course.id, title="")
                    db.add(topic)
                    topics_by_slug[tdoc["slug"]] = topic
                topic.course_id = course.id
                topic.unit = unit.get("title", "")
                topic.title = tdoc["title"]
                topic.description = tdoc.get("description", "")
                topic.est_minutes = tdoc.get("est_minutes", 10)
                topic.generator_keys = tdoc.get("generators", [])
                topic.status = "active"
                db.flush()
                stats["topics"] += 1

                for p in tdoc.get("prereqs", []):
                    pending_edges.append((p, tdoc["slug"], "hard"))
                for p in tdoc.get("soft_prereqs", []):
                    pending_edges.append((p, tdoc["slug"], "soft"))

                _sync_lesson(db, topic, tdoc, stats)
                _sync_resources(db, topic, tdoc.get("resources", []), stats)

    _sync_edges(db, topics_by_slug, pending_edges, stats)
    db.flush()

    # Validate acyclicity and persist depth ranks over the whole graph.
    graph = TopicGraph.load(db, include_draft=True)
    for tid, rank in graph.depth_ranks().items():
        graph.topics[tid].depth_rank = rank

    db.commit()
    return stats


def _sync_lesson(db: Session, topic: Topic, tdoc: dict, stats: dict) -> None:
    if "lesson" not in tdoc:
        return
    lesson = db.scalar(
        select(Lesson).where(Lesson.topic_id == topic.id, Lesson.source == "seed")
    )
    if lesson is None:
        lesson = Lesson(topic_id=topic.id, source="seed", content_md="")
        db.add(lesson)
    lesson.content_md = tdoc["lesson"]
    lesson.worked_examples = [
        {"problem_md": ex["problem"], "solution_md": ex["solution"]}
        for ex in tdoc.get("worked_examples", [])
    ]
    stats["lessons"] += 1


def _sync_resources(db: Session, topic: Topic, docs: list[dict], stats: dict) -> None:
    existing = {r.url: r for r in db.scalars(select(Resource).where(Resource.topic_id == topic.id))}
    wanted_urls = set()
    for rdoc in docs:
        wanted_urls.add(rdoc["url"])
        res = existing.get(rdoc["url"])
        if res is None:
            res = Resource(topic_id=topic.id, url=rdoc["url"], title="")
            db.add(res)
        res.kind = rdoc.get("kind", "link")
        res.title = rdoc["title"]
        res.note = rdoc.get("note", "")
        stats["resources"] += 1
    for url, res in existing.items():
        if url not in wanted_urls:
            db.delete(res)


def _sync_edges(
    db: Session,
    topics_by_slug: dict[str, Topic],
    pending: list[tuple[str, str, str]],
    stats: dict,
) -> None:
    wanted: dict[tuple[int, int], str] = {}
    for prereq_slug, topic_slug, kind in pending:
        prereq = topics_by_slug.get(prereq_slug)
        if prereq is None:
            raise ValueError(f"unknown prereq slug {prereq_slug!r} (needed by {topic_slug!r})")
        wanted[(prereq.id, topics_by_slug[topic_slug].id)] = kind

    existing = {
        (e.prereq_id, e.topic_id): e
        for e in db.scalars(select(TopicEdge).where(TopicEdge.source == "seed"))
    }
    for key, kind in wanted.items():
        edge = existing.get(key)
        if edge is None:
            db.add(TopicEdge(prereq_id=key[0], topic_id=key[1], kind=kind, source="seed"))
        else:
            edge.kind = kind
        stats["edges"] += 1
    for key, edge in existing.items():
        if key not in wanted:
            db.delete(edge)
