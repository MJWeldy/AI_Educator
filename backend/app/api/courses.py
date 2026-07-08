from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from .deps import current_profile_id
from ..engine.graph import TopicGraph, effective_masteries
from ..models import Course, Lesson, Mastery, Topic
from ..schemas import CourseDetail, CourseSummary, TopicNode, UnitOut

router = APIRouter(prefix="/api/courses", tags=["courses"])


def _summarize(course: Course, masteries: dict[int, str], topics: list[Topic]) -> dict:
    return {
        "id": course.id,
        "slug": course.slug,
        "title": course.title,
        "description": course.description,
        "level": course.level,
        "sequence_order": course.sequence_order,
        "document_id": course.document_id,
        "source": course.source,
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
    courses = db.scalars(select(Course).order_by(Course.sequence_order)).all()
    by_course: dict[int, list[Topic]] = {}
    for t in graph.topics.values():  # graph holds active topics only
        by_course.setdefault(t.course_id, []).append(t)
    return [
        _summarize(c, masteries, by_course.get(c.id, []))
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

    summary = _summarize(course, masteries, topics)
    return CourseDetail(
        **summary,
        units=[UnitOut(title=name, topics=nodes) for name, nodes in units.items()],
    )
