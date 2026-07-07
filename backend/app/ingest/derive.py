"""Stage 3: LLM derives teachable topics from each section, then a graph pass
adds prerequisite edges and welds the new topics into the seed graph."""

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..llm import router
from ..llm.base import JobType, Message
from ..llm.cache import cached_complete_json
from ..models import Course, Document, DocumentSection, Topic, TopicEdge

TOPICS_SCHEMA = {
    "type": "object",
    "properties": {
        "topics": {
            "type": "array",
            "maxItems": 4,
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "est_minutes": {"type": "integer"},
                },
                "required": ["title", "description", "est_minutes"],
            },
        }
    },
    "required": ["topics"],
}

TOPICS_SYSTEM = """You extract teachable topics from a textbook section for a
mastery-based math learning app. A topic is one specific skill or concept a student
can learn in 5-20 minutes and be tested on (like "Adding fractions with unlike
denominators" — not "Chapter 3"). Emit 0-4 topics for the section: fewer, sharper
topics beat many vague ones. Skip prefaces, exercises-only sections, and reviews.
est_minutes is a realistic 5-20."""

EDGES_SCHEMA = {
    "type": "object",
    "properties": {
        "edges": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "topic": {"type": "integer", "description": "index of the dependent topic"},
                    "requires": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "indexes of prerequisite topics in this list",
                    },
                    "requires_seed": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "slugs of prerequisite topics from the existing curriculum",
                    },
                },
                "required": ["topic", "requires", "requires_seed"],
            },
        }
    },
    "required": ["edges"],
}

EDGES_SYSTEM = """You connect new textbook topics into a prerequisite graph.
For each numbered topic, list which other topics in the list must be learned first
(by index), and which existing-curriculum topics (by slug, from the provided
candidates only) are prerequisites. Only genuine hard prerequisites — knowledge
truly required, not merely related. Earlier chapters usually feed later ones."""


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:60] or "topic"


def _seed_candidates(db: Session, titles: list[str], limit: int = 30) -> list[Topic]:
    """Cheap keyword prefilter over the seed curriculum."""
    words = set()
    for t in titles:
        words |= {w for w in re.findall(r"[a-z]{4,}", t.lower())}
    seed_topics = db.scalars(select(Topic).where(Topic.source == "seed")).all()
    scored = []
    for topic in seed_topics:
        hay = f"{topic.title} {topic.description}".lower()
        score = sum(1 for w in words if w in hay)
        if score:
            scored.append((score, topic))
    scored.sort(key=lambda x: -x[0])
    return [t for _, t in scored[:limit]]


async def derive_topics(db: Session, doc: Document, progress=None) -> Course:
    course = db.scalar(select(Course).where(Course.document_id == doc.id))
    if course is None:
        max_seq = max((c.sequence_order for c in db.scalars(select(Course))), default=0)
        course = Course(
            slug=f"doc-{doc.id}-{slugify(doc.title or doc.filename)}",
            title=doc.title or doc.filename,
            description=f"Generated from your upload “{doc.filename}”.",
            sequence_order=max_seq + 10,
            source="document",
            document_id=doc.id,
        )
        db.add(course)
        db.commit()

    chapters = db.scalars(
        select(DocumentSection)
        .where(DocumentSection.document_id == doc.id, DocumentSection.level == 1)
        .order_by(DocumentSection.position)
    ).all()

    for ci, chapter in enumerate(chapters):
        children = db.scalars(
            select(DocumentSection)
            .where(DocumentSection.parent_id == chapter.id)
            .order_by(DocumentSection.position)
        ).all() or [chapter]

        chapter_topics: list[Topic] = []
        for section in children:
            # Checkpoint: skip sections that already produced topics.
            existing = db.scalars(
                select(Topic).where(Topic.document_section_id == section.id)
            ).all()
            if existing:
                chapter_topics.extend(existing)
                continue
            if not section.text.strip():
                continue
            choice = router.resolve(db, JobType.ingest_topics)
            result = await cached_complete_json(
                db,
                choice,
                JobType.ingest_topics,
                [
                    Message("system", TOPICS_SYSTEM),
                    Message(
                        "user",
                        f"Book: {doc.title or doc.filename}\nChapter: {chapter.title}\n"
                        f"Section: {section.title}\n\nSection text:\n{section.text[:12000]}",
                    ),
                ],
                TOPICS_SCHEMA,
            )
            for tdoc in result.get("topics", []):
                slug = f"doc{doc.id}-{slugify(tdoc['title'])}"
                base, i = slug, 2
                while db.scalar(select(Topic).where(Topic.slug == slug)) is not None:
                    slug = f"{base}-{i}"
                    i += 1
                topic = Topic(
                    slug=slug,
                    course_id=course.id,
                    unit=chapter.title[:120],
                    title=tdoc["title"][:200],
                    description=tdoc.get("description", "")[:500],
                    est_minutes=max(5, min(20, int(tdoc.get("est_minutes", 10)))),
                    source="document",
                    document_section_id=section.id,
                    status="draft",
                )
                db.add(topic)
                db.flush()
                chapter_topics.append(topic)
            db.commit()
            if progress:
                progress("deriving topics", ci + 1, len(chapters), section.title)

        await _derive_edges(db, doc, chapter, chapter_topics)
    return course


async def _derive_edges(db: Session, doc: Document, chapter, topics: list[Topic]) -> None:
    if not topics:
        return
    has_edges = db.scalar(
        select(TopicEdge).where(TopicEdge.topic_id.in_([t.id for t in topics]))
    )
    if has_edges is not None:
        return  # checkpoint

    candidates = _seed_candidates(db, [t.title for t in topics])
    topic_list = "\n".join(f"{i}. {t.title} — {t.description}" for i, t in enumerate(topics))
    cand_list = "\n".join(f"- {t.slug}: {t.title}" for t in candidates) or "(none)"

    choice = router.resolve(db, JobType.topic_mapping)
    result = await cached_complete_json(
        db,
        choice,
        JobType.topic_mapping,
        [
            Message("system", EDGES_SYSTEM),
            Message(
                "user",
                f"Chapter: {chapter.title}\n\nNew topics:\n{topic_list}\n\n"
                f"Existing curriculum candidates:\n{cand_list}",
            ),
        ],
        EDGES_SCHEMA,
    )

    cand_by_slug = {t.slug: t for t in candidates}
    seen: set[tuple[int, int]] = set()
    for edge in result.get("edges", []):
        ti = edge.get("topic", -1)
        if not (0 <= ti < len(topics)):
            continue
        dependent = topics[ti]
        for ri in edge.get("requires", []):
            if 0 <= ri < len(topics) and ri != ti:
                key = (topics[ri].id, dependent.id)
                if key not in seen:
                    seen.add(key)
                    db.add(TopicEdge(prereq_id=key[0], topic_id=key[1], kind="hard", source="document"))
        for slug in edge.get("requires_seed", []):
            seed_topic = cand_by_slug.get(slug)
            if seed_topic is not None:
                key = (seed_topic.id, dependent.id)
                if key not in seen:
                    seen.add(key)
                    # Soft: welds the book into the curriculum graph without
                    # locking it behind coursework — uploads are startable now.
                    db.add(TopicEdge(prereq_id=key[0], topic_id=key[1], kind="soft", source="document"))
    # Drop any accidental cycles: keep the graph loadable.
    db.commit()
    from ..engine.graph import CycleError, TopicGraph

    try:
        TopicGraph.load(db, include_draft=True).topological_order()
    except CycleError:
        for t in topics:
            for e in db.scalars(select(TopicEdge).where(TopicEdge.topic_id == t.id, TopicEdge.source == "document")):
                db.delete(e)
        db.commit()
