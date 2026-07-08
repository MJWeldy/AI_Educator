from pydantic import BaseModel


class ResourceOut(BaseModel):
    kind: str
    title: str
    url: str
    note: str = ""


class TopicNode(BaseModel):
    id: int
    slug: str
    title: str
    unit: str
    description: str
    est_minutes: int
    depth_rank: int
    mastery: str
    prereq_ids: list[int]
    has_lesson: bool
    fsrs_due_at: str | None = None


class UnitOut(BaseModel):
    title: str
    topics: list[TopicNode]


class CourseSummary(BaseModel):
    id: int
    slug: str
    title: str
    description: str
    level: str = ""
    document_id: int | None = None
    sequence_order: int
    source: str
    topic_count: int
    learned_count: int
    mastered_count: int


class CourseDetail(CourseSummary):
    units: list[UnitOut]


class WorkedExample(BaseModel):
    problem_md: str
    solution_md: str


class LessonOut(BaseModel):
    content_md: str
    worked_examples: list[WorkedExample]
    source: str


class TopicDetail(BaseModel):
    id: int
    slug: str
    title: str
    unit: str
    description: str
    course_slug: str
    course_title: str
    est_minutes: int
    mastery: str
    generator_keys: list[str]
    lesson: LessonOut | None
    resources: list[ResourceOut]
    prereqs: list[TopicNode]
