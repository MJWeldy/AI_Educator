from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from .deps import current_profile_id
from ..engine import scheduler
from ..engine.graph import TopicGraph, effective_masteries
from ..models import Course, Enrollment, Lesson, Mastery, Topic
from ..schemas import CourseDetail, CourseSummary, TopicNode, UnitOut

router = APIRouter(prefix="/api/courses", tags=["courses"])


def _enrolled_course_ids(db: Session, profile_id: int) -> set[int]:
    return set(
        db.scalars(select(Enrollment.course_id).where(Enrollment.profile_id == profile_id))
    )


def _summarize(
    course: Course, masteries: dict[int, str], topics: list[Topic], enrolled_ids: set[int] = frozenset()
) -> dict:
    return {
        "id": course.id,
        "slug": course.slug,
        "title": course.title,
        "description": course.description,
        "level": course.level,
        "category": course.category,
        "sequence_order": course.sequence_order,
        "document_id": course.document_id,
        "source": course.source,
        "enrolled": course.id in enrolled_ids,
        "topic_count": len(topics),
        "learned_count": sum(
            1
            for t in topics
            if masteries.get(t.id) in (Mastery.learned.value, Mastery.mastered.value)
        ),
        "mastered_count": sum(
            1 for t in topics if masteries.get(t.id) == Mastery.mastered.value
        ),
    }


@router.get("", response_model=list[CourseSummary])
def list_courses(
    db: Session = Depends(get_db), profile_id: int = Depends(current_profile_id)
):
    graph = TopicGraph.load(db)
    masteries = effective_masteries(db, graph, profile_id)
    enrolled = _enrolled_course_ids(db, profile_id)
    courses = db.scalars(select(Course).order_by(Course.sequence_order)).all()
    by_course: dict[int, list[Topic]] = {}
    for t in graph.topics.values():  # graph holds active topics only
        by_course.setdefault(t.course_id, []).append(t)
    return [
        _summarize(c, masteries, by_course.get(c.id, []), enrolled)
        for c in courses
        # Document courses stay hidden until review publishes their topics.
        if c.source != "document" or by_course.get(c.id)
    ]


@router.get("/{slug}", response_model=CourseDetail)
def get_course(
    slug: str,
    db: Session = Depends(get_db),
    profile_id: int = Depends(current_profile_id),
):
    course = db.scalar(select(Course).where(Course.slug == slug))
    if course is None:
        raise HTTPException(404, "course not found")
    graph = TopicGraph.load(db)
    masteries = effective_masteries(db, graph, profile_id)

    topics = sorted(
        (t for t in graph.topics.values() if t.course_id == course.id),
        key=lambda t: (t.depth_rank, t.id),
    )
    with_lessons = set(
        db.scalars(select(Lesson.topic_id).where(Lesson.topic_id.in_([t.id for t in topics])))
    )

    units: dict[str, list[TopicNode]] = {}
    for t in topics:
        units.setdefault(t.unit, []).append(
            TopicNode(
                id=t.id,
                slug=t.slug,
                title=t.title,
                unit=t.unit,
                description=t.description,
                est_minutes=t.est_minutes,
                depth_rank=t.depth_rank,
                mastery=masteries.get(t.id, Mastery.locked.value),
                prereq_ids=sorted(graph.all_prereqs(t.id)),
                has_lesson=t.id in with_lessons,
            )
        )

    summary = _summarize(course, masteries, topics, _enrolled_course_ids(db, profile_id))
    return CourseDetail(
        **summary,
        units=[UnitOut(title=name, topics=nodes) for name, nodes in units.items()],
    )


@router.put("/{slug}/enroll", response_model=CourseSummary)
def enroll(
    slug: str,
    db: Session = Depends(get_db),
    profile_id: int = Depends(current_profile_id),
):
    course = db.scalar(select(Course).where(Course.slug == slug))
    if course is None:
        raise HTTPException(404, "course not found")
    if db.get(Enrollment, (profile_id, course.id)) is None:
        db.add(Enrollment(profile_id=profile_id, course_id=course.id))
        db.commit()
        scheduler.reset_today_if_fresh(db, profile_id)
    return _course_summary(db, course, profile_id)


@router.delete("/{slug}/enroll", response_model=CourseSummary)
def unenroll(
    slug: str,
    db: Session = Depends(get_db),
    profile_id: int = Depends(current_profile_id),
):
    course = db.scalar(select(Course).where(Course.slug == slug))
    if course is None:
        raise HTTPException(404, "course not found")
    row = db.get(Enrollment, (profile_id, course.id))
    if row is not None:
        db.delete(row)
        db.commit()
        scheduler.reset_today_if_fresh(db, profile_id)
    return _course_summary(db, course, profile_id)


def _course_summary(db: Session, course: Course, profile_id: int) -> CourseSummary:
    graph = TopicGraph.load(db)
    masteries = effective_masteries(db, graph, profile_id)
    topics = [t for t in graph.topics.values() if t.course_id == course.id]
    return CourseSummary(**_summarize(course, masteries, topics, _enrolled_course_ids(db, profile_id)))


class CoursePatch(BaseModel):
    title: str | None = None
    category: str | None = None


@router.patch("/{slug}", response_model=CourseSummary)
def update_course(slug: str, body: CoursePatch, db: Session = Depends(get_db)):
    """Edit an uploaded course's title/category. Seed courses are managed by the
    curriculum files and re-sync at startup, so edits to them wouldn't stick."""
    course = db.scalar(select(Course).where(Course.slug == slug))
    if course is None:
        raise HTTPException(404, "course not found")
    if course.source != "document":
        raise HTTPException(409, "built-in courses are edited in the curriculum files")
    if body.title is not None:
        title = body.title.strip()
        if not title:
            raise HTTPException(400, "title required")
        course.title = title[:120]
        if course.document_id is not None:
            from ..models import Document

            doc = db.get(Document, course.document_id)
            if doc is not None:
                doc.title = course.title
    if body.category is not None:
        course.category = body.category.strip()[:60]
    db.commit()
    return _course_summary(db, course, 1)
