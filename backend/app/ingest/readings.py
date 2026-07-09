"""Attach a "reading" resource to each document-derived topic, pointing back at
the book section the topic was distilled from (section title + page range).

Grounded entirely in the source — no LLM, no fabricated citations — so it is
safe to (re)run: it is idempotent, skipping topics that already have a reading.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Course, Document, DocumentSection, Resource, Topic


def _page_range(section: DocumentSection) -> str:
    """Human 1-based inclusive page range; stored indices are 0-based."""
    if section.page_end and section.page_end >= section.page_start:
        a, b = section.page_start + 1, section.page_end + 1
        return f"pp. {a}–{b}" if b > a else f"p. {a}"
    return ""


def reading_for(book: str, section: DocumentSection) -> tuple[str, str]:
    """Return (title, note) for a source-section reading. Fallback page-chunk
    section titles ("Pages 41–50") already encode the range, so we don't repeat
    it; named sections get the book + page range as the note."""
    loc = (section.title or "").strip()
    if loc.lower().startswith("page"):
        return loc, book
    note = " · ".join(x for x in [book, _page_range(section)] if x)
    return loc or book, note


def attach_readings(db: Session, doc: Document) -> int:
    """Create a reading resource for every document topic that lacks one.
    Returns the number added. For folder uploads the source cited is the
    specific file (the section's parent chapter); for a single book it's the
    book title."""
    course = db.scalar(select(Course).where(Course.document_id == doc.id))
    if course is None:
        return 0
    book = doc.title or doc.filename
    multi = len(doc.files) > 1
    topics = db.scalars(
        select(Topic).where(Topic.course_id == course.id, Topic.source == "document")
    ).all()
    added = 0
    for t in topics:
        if t.document_section_id is None:
            continue
        exists = db.scalar(
            select(Resource).where(Resource.topic_id == t.id, Resource.kind == "reading")
        )
        if exists is not None:
            continue
        section = db.get(DocumentSection, t.document_section_id)
        if section is None:
            continue
        source = book
        if multi and section.parent_id is not None:
            parent = db.get(DocumentSection, section.parent_id)
            if parent is not None and parent.title:
                source = parent.title  # the file this topic came from
        title, note = reading_for(source, section)
        if note == title:  # e.g. a whole short text file — don't repeat it
            note = ""
        db.add(Resource(topic_id=t.id, kind="reading", title=title, url="", note=note))
        added += 1
    db.commit()
    return added
