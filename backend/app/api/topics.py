from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..engine.graph import TopicGraph, effective_masteries
from ..models import Lesson, Mastery, Topic
from ..schemas import LessonOut, ResourceOut, TopicDetail, TopicNode, WorkedExample

router = APIRouter(prefix="/api/topics", tags=["topics"])

PROFILE_ID = 1


@router.get("/{topic_id}", response_model=TopicDetail)
def get_topic(topic_id: int, db: Session = Depends(get_db)):
    topic = db.get(Topic, topic_id)
    if topic is None:
        raise HTTPException(404, "topic not found")
    graph = TopicGraph.load(db)
    masteries = effective_masteries(db, graph, PROFILE_ID)

    lesson = db.scalar(
        select(Lesson)
        .where(Lesson.topic_id == topic.id, Lesson.review_status == "approved")
        .order_by(Lesson.position)
    )
    lesson_out = None
    if lesson is not None:
        lesson_out = LessonOut(
            content_md=lesson.content_md,
            worked_examples=[WorkedExample(**ex) for ex in lesson.worked_examples],
            source=lesson.source,
        )

    prereq_nodes = []
    for pid in sorted(graph.all_prereqs(topic.id)):
        p = graph.topics[pid]
        prereq_nodes.append(
            TopicNode(
                id=p.id,
                slug=p.slug,
                title=p.title,
                unit=p.unit,
                description=p.description,
                est_minutes=p.est_minutes,
                depth_rank=p.depth_rank,
                mastery=masteries.get(p.id, Mastery.locked.value),
                prereq_ids=sorted(graph.all_prereqs(p.id)),
                has_lesson=False,
            )
        )

    return TopicDetail(
        id=topic.id,
        slug=topic.slug,
        title=topic.title,
        unit=topic.unit,
        description=topic.description,
        course_slug=topic.course.slug,
        course_title=topic.course.title,
        est_minutes=topic.est_minutes,
        mastery=masteries.get(topic.id, Mastery.locked.value),
        generator_keys=topic.generator_keys,
        lesson=lesson_out,
        resources=[
            ResourceOut(kind=r.kind, title=r.title, url=r.url, note=r.note)
            for r in topic.resources
        ],
        prereqs=prereq_nodes,
    )
