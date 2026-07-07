import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import jobs
from ..config import settings
from ..db import get_db
from ..models import Course, Document, DocumentSection, Job, Lesson, Problem, Topic, TopicEdge

router = APIRouter(prefix="/api/documents", tags=["documents"])


class DocumentOut(BaseModel):
    id: int
    filename: str
    title: str
    status: str
    error: str | None
    page_count: int
    topic_count: int
    progress: dict | None


def _doc_out(db: Session, doc: Document) -> DocumentOut:
    topic_count = len(
        db.scalars(
            select(Topic.id)
            .join(DocumentSection, Topic.document_section_id == DocumentSection.id)
            .where(DocumentSection.document_id == doc.id)
        ).all()
    )
    job = db.scalar(
        select(Job)
        .where(Job.kind == "ingest_document")
        .order_by(Job.id.desc())
    )
    progress = None
    if job is not None and job.payload.get("document_id") == doc.id:
        progress = {**(job.progress or {}), "job_status": job.status}
    return DocumentOut(
        id=doc.id,
        filename=doc.filename,
        title=doc.title,
        status=doc.status,
        error=doc.error,
        page_count=doc.page_count,
        topic_count=topic_count,
        progress=progress,
    )


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db)):
    docs = db.scalars(select(Document).order_by(Document.id.desc())).all()
    return [_doc_out(db, d) for d in docs]


@router.post("", response_model=DocumentOut)
async def upload(file: UploadFile, db: Session = Depends(get_db)):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "only PDF files are supported")
    uploads = Path(settings.uploads_dir)
    uploads.mkdir(parents=True, exist_ok=True)
    doc = Document(filename=file.filename, stored_path="")
    db.add(doc)
    db.flush()
    dest = uploads / f"{doc.id}-{Path(file.filename).name}"
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    doc.stored_path = str(dest)
    db.commit()
    jobs.enqueue(db, "ingest_document", {"document_id": doc.id})
    return _doc_out(db, doc)


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(404, "document not found")
    return _doc_out(db, doc)


class ReviewProblem(BaseModel):
    id: int
    statement_md: str
    parts: list[dict]
    solution_md: str
    difficulty: int
    answer_verified: bool


class ReviewTopic(BaseModel):
    id: int
    title: str
    unit: str
    description: str
    est_minutes: int
    prereq_titles: list[str]
    lesson_md: str | None
    worked_examples: list[dict]
    problems: list[ReviewProblem]


class ReviewOut(BaseModel):
    document: DocumentOut
    course_slug: str | None
    course_title: str | None
    topics: list[ReviewTopic]


@router.get("/{doc_id}/review", response_model=ReviewOut)
def review(doc_id: int, db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(404, "document not found")
    course = db.scalar(select(Course).where(Course.document_id == doc.id))
    topics = []
    if course is not None:
        topic_rows = db.scalars(
            select(Topic).where(Topic.course_id == course.id).order_by(Topic.id)
        ).all()
        titles = {t.id: t.title for t in db.scalars(select(Topic))}
        for t in topic_rows:
            lesson = db.scalar(select(Lesson).where(Lesson.topic_id == t.id))
            problems = db.scalars(select(Problem).where(Problem.topic_id == t.id)).all()
            prereq_ids = db.scalars(
                select(TopicEdge.prereq_id).where(TopicEdge.topic_id == t.id)
            ).all()
            topics.append(
                ReviewTopic(
                    id=t.id,
                    title=t.title,
                    unit=t.unit,
                    description=t.description,
                    est_minutes=t.est_minutes,
                    prereq_titles=[titles.get(p, "?") for p in prereq_ids],
                    lesson_md=lesson.content_md if lesson else None,
                    worked_examples=lesson.worked_examples if lesson else [],
                    problems=[
                        ReviewProblem(
                            id=p.id,
                            statement_md=p.statement_md,
                            parts=p.parts,
                            solution_md=p.solution_md,
                            difficulty=p.difficulty,
                            answer_verified=p.answer_verified,
                        )
                        for p in problems
                    ],
                )
            )
    return ReviewOut(
        document=_doc_out(db, doc),
        course_slug=course.slug if course else None,
        course_title=course.title if course else None,
        topics=topics,
    )


@router.delete("/{doc_id}/topics/{topic_id}")
def delete_topic(doc_id: int, topic_id: int, db: Session = Depends(get_db)):
    topic = db.get(Topic, topic_id)
    if topic is None or topic.source != "document":
        raise HTTPException(404, "draft topic not found")
    for edge in db.scalars(
        select(TopicEdge).where(
            (TopicEdge.topic_id == topic_id) | (TopicEdge.prereq_id == topic_id)
        )
    ):
        db.delete(edge)
    for lesson in db.scalars(select(Lesson).where(Lesson.topic_id == topic_id)):
        db.delete(lesson)
    for problem in db.scalars(select(Problem).where(Problem.topic_id == topic_id)):
        db.delete(problem)
    db.delete(topic)
    db.commit()
    return {"ok": True}


@router.delete("/{doc_id}/problems/{problem_id}")
def delete_problem(doc_id: int, problem_id: int, db: Session = Depends(get_db)):
    problem = db.get(Problem, problem_id)
    if problem is None:
        raise HTTPException(404, "problem not found")
    db.delete(problem)
    db.commit()
    return {"ok": True}


@router.post("/{doc_id}/retry", response_model=DocumentOut)
def retry(doc_id: int, db: Session = Depends(get_db)):
    """Re-enqueue ingestion; completed stages are checkpointed so this resumes."""
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(404, "document not found")
    if doc.status in ("review", "published"):
        raise HTTPException(409, "document already ingested")
    active = db.scalar(
        select(Job).where(Job.kind == "ingest_document", Job.status.in_(["queued", "running"]))
    )
    if active is not None and active.payload.get("document_id") == doc.id:
        raise HTTPException(409, "ingestion already running")
    doc.error = None
    db.commit()
    jobs.enqueue(db, "ingest_document", {"document_id": doc.id})
    return _doc_out(db, doc)


@router.post("/{doc_id}/publish", response_model=DocumentOut)
def publish(doc_id: int, db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(404, "document not found")
    if doc.status != "review":
        raise HTTPException(409, f"document is {doc.status}, not ready to publish")
    course = db.scalar(select(Course).where(Course.document_id == doc.id))
    if course is None:
        raise HTTPException(409, "no derived course to publish")
    for topic in db.scalars(select(Topic).where(Topic.course_id == course.id)):
        topic.status = "active"
        for lesson in db.scalars(select(Lesson).where(Lesson.topic_id == topic.id)):
            lesson.review_status = "approved"
        for problem in db.scalars(select(Problem).where(Problem.topic_id == topic.id)):
            problem.review_status = "approved"
    doc.status = "published"
    db.commit()
    return _doc_out(db, doc)
