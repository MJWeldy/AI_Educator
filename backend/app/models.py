import enum
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Mastery(str, enum.Enum):
    locked = "locked"
    unlocked = "unlocked"
    learning = "learning"
    learned = "learned"
    mastered = "mastered"


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String, unique=True, index=True)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text, default="")
    level: Mapped[str] = mapped_column(String, default="")  # e.g. "Grades 3–8", "Undergraduate"
    sequence_order: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String, default="seed")  # seed | document
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"), nullable=True)

    topics: Mapped[list["Topic"]] = relationship(back_populates="course")


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String, unique=True, index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    unit: Mapped[str] = mapped_column(String, default="")  # display grouping within a course
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text, default="")
    depth_rank: Mapped[int] = mapped_column(Integer, default=0)  # longest prereq chain, loader-filled
    est_minutes: Mapped[int] = mapped_column(Integer, default=10)
    generator_keys: Mapped[list] = mapped_column(JSON, default=list)
    source: Mapped[str] = mapped_column(String, default="seed")  # seed | document
    document_section_id: Mapped[int | None] = mapped_column(
        ForeignKey("document_sections.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String, default="active")  # active | draft

    course: Mapped[Course] = relationship(back_populates="topics")
    lessons: Mapped[list["Lesson"]] = relationship(back_populates="topic")
    resources: Mapped[list["Resource"]] = relationship(back_populates="topic")


class TopicEdge(Base):
    __tablename__ = "topic_edges"

    prereq_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), primary_key=True)
    kind: Mapped[str] = mapped_column(String, default="hard")  # hard gates unlock; soft biases only
    source: Mapped[str] = mapped_column(String, default="seed")


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    content_md: Mapped[str] = mapped_column(Text)
    worked_examples: Mapped[list] = mapped_column(JSON, default=list)  # [{problem_md, solution_md}]
    source: Mapped[str] = mapped_column(String, default="seed")  # seed | llm | document
    model: Mapped[str | None] = mapped_column(String, nullable=True)
    review_status: Mapped[str] = mapped_column(String, default="approved")  # draft | approved
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    topic: Mapped[Topic] = relationship(back_populates="lessons")


class Problem(Base):
    __tablename__ = "problems"

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), index=True)
    statement_md: Mapped[str] = mapped_column(Text)
    # parts: [{prompt_md, answer_type, canonical, tolerance?, choices?}]
    parts: Mapped[list] = mapped_column(JSON, default=list)
    solution_md: Mapped[str] = mapped_column(Text, default="")
    difficulty: Mapped[int] = mapped_column(Integer, default=1)  # 1..3 scaffold tier
    answer_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String, default="seed")  # seed | llm | document
    model: Mapped[str | None] = mapped_column(String, nullable=True)
    review_status: Mapped[str] = mapped_column(String, default="approved")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), index=True)
    kind: Mapped[str] = mapped_column(String, default="link")  # video | reading | link
    title: Mapped[str] = mapped_column(String)
    url: Mapped[str] = mapped_column(String)
    note: Mapped[str] = mapped_column(Text, default="")

    topic: Mapped[Topic] = relationship(back_populates="resources")


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, default="Learner")


class UserTopicState(Base):
    __tablename__ = "user_topic_state"

    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), primary_key=True)
    mastery: Mapped[str] = mapped_column(String, default=Mastery.unlocked.value)
    # lesson_progress: {tier, correct_streak, misses_at_tier, problems_done, seeds_used}
    lesson_progress: Mapped[dict] = mapped_column(JSON, default=dict)
    fsrs_card: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # py-fsrs Card.to_dict()
    fsrs_due_at: Mapped[datetime | None] = mapped_column(nullable=True)
    fsrs_stability: Mapped[float | None] = mapped_column(Float, nullable=True)
    reps: Mapped[int] = mapped_column(Integer, default=0)
    lapses: Mapped[int] = mapped_column(Integer, default=0)
    placed_by_diagnostic: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), index=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), index=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"), nullable=True)
    problem_id: Mapped[int | None] = mapped_column(ForeignKey("problems.id"), nullable=True)
    generator_key: Mapped[str | None] = mapped_column(String, nullable=True)
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    difficulty: Mapped[int] = mapped_column(Integer, default=1)
    presented: Mapped[dict] = mapped_column(JSON, default=dict)  # full instance snapshot
    user_answer: Mapped[dict] = mapped_column(JSON, default=dict)
    correct: Mapped[bool] = mapped_column(Boolean, default=False)
    part_results: Mapped[list] = mapped_column(JSON, default=list)
    hints_used: Mapped[int] = mapped_column(Integer, default=0)
    time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    context: Mapped[str] = mapped_column(String, default="lesson")  # lesson|review|quiz|diagnostic
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), index=True)
    type: Mapped[str] = mapped_column(String)  # lesson | review | quiz | diagnostic
    topic_ids: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String, default="pending")  # pending | active | done | skipped
    for_date: Mapped[str] = mapped_column(String, index=True)  # YYYY-MM-DD local date
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    xp_value: Mapped[int] = mapped_column(Integer, default=0)
    xp_awarded: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class XpEntry(Base):
    __tablename__ = "xp_ledger"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"), nullable=True)
    for_date: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class DiagnosticSession(Base):
    __tablename__ = "diagnostic_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), index=True)
    course_scope: Mapped[list] = mapped_column(JSON, default=list)  # course slugs
    status: Mapped[str] = mapped_column(String, default="active")  # active | finished | abandoned
    belief: Mapped[dict] = mapped_column(JSON, default=dict)  # topic_id(str) -> P(known)
    asked: Mapped[list] = mapped_column(JSON, default=list)  # [{topic_id, correct}]
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String)
    stored_path: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String, default="")
    # uploaded|extracting|segmenting|deriving|generating|review|published|failed
    status: Mapped[str] = mapped_column(String, default="uploaded")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class DocumentSection(Base):
    __tablename__ = "document_sections"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("document_sections.id"), nullable=True)
    level: Mapped[int] = mapped_column(Integer, default=1)
    position: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String)
    page_start: Mapped[int] = mapped_column(Integer, default=0)
    page_end: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text, default="")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="queued")  # queued|running|done|failed|cancelled
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    progress: Mapped[dict] = mapped_column(JSON, default=dict)  # {stage, current, total, message}
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class LLMCacheEntry(Base):
    __tablename__ = "llm_cache"
    __table_args__ = (UniqueConstraint("cache_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    cache_key: Mapped[str] = mapped_column(String, index=True)
    job_type: Mapped[str] = mapped_column(String)
    provider: Mapped[str] = mapped_column(String)
    model: Mapped[str] = mapped_column(String)
    response: Mapped[str] = mapped_column(Text)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class SettingRow(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[dict | list | str | int | float | None] = mapped_column(JSON, nullable=True)
