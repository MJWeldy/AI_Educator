"""On-demand LLM content: lesson text for topics without a hand-written one,
hints during practice, and mistake explanations. Lessons are cached in the DB
(as Lesson rows) so nothing is generated twice."""

from collections.abc import AsyncIterator

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..engine.graph import TopicGraph
from ..llm import router
from ..llm.base import JobType, Message
from ..llm.cache import cached_complete_json
from ..models import Lesson, Topic
from .worked_examples import normalize_worked_examples

LESSON_SCHEMA = {
    "type": "object",
    "properties": {
        "content_md": {
            "type": "string",
            "description": "The lesson body in Markdown with $...$ / $$...$$ LaTeX math.",
        },
        "worked_examples": {
            "type": "array",
            "minItems": 2,
            "maxItems": 3,
            "items": {
                "type": "object",
                "properties": {
                    "problem_md": {"type": "string"},
                    "solution_md": {"type": "string"},
                },
                "required": ["problem_md", "solution_md"],
            },
        },
    },
    "required": ["content_md", "worked_examples"],
}

LESSON_SYSTEM = """You are a master mathematics teacher writing a short lesson for a
mastery-based learning app (in the style of Math Academy). Write concisely and
concretely: motivate the idea in a sentence or two, state the key rule or method,
and show how it works. Use Markdown with LaTeX math ($...$ inline, $$...$$ display).
Aim for 150-350 words of lesson body, then 2-3 fully worked examples that go from
easy to moderate. Never reference 'this app' or the student's history."""


async def generate_lesson(db: Session, topic: Topic) -> Lesson:
    existing = db.scalar(
        select(Lesson).where(Lesson.topic_id == topic.id).order_by(Lesson.position)
    )
    if existing is not None:
        return existing

    graph = TopicGraph.load(db)
    prereq_titles = [graph.topics[p].title for p in graph.all_prereqs(topic.id) if p in graph.topics]
    context = f"Course: {topic.course.title}\nUnit: {topic.unit}\nTopic: {topic.title}"
    if topic.description:
        context += f"\nTopic scope: {topic.description}"
    if prereq_titles:
        context += "\nThe student has already learned: " + ", ".join(prereq_titles)

    choice = router.resolve(db, JobType.lesson_text)
    result = await cached_complete_json(
        db,
        choice,
        JobType.lesson_text,
        [Message("system", LESSON_SYSTEM), Message("user", f"Write the lesson.\n\n{context}")],
        LESSON_SCHEMA,
    )

    lesson = Lesson(
        topic_id=topic.id,
        content_md=result["content_md"],
        worked_examples=normalize_worked_examples(result.get("worked_examples")),
        source="llm",
        model=f"{choice.provider_name}:{choice.model}",
        review_status="approved",
    )
    db.add(lesson)
    db.commit()
    return lesson


HINT_SYSTEM = """You are a patient math tutor. The student is stuck on a problem.
Give ONE short hint (2-4 sentences) that nudges them toward the next step without
revealing the final answer. Use LaTeX math in $...$ where helpful."""

EXPLAIN_SYSTEM = """You are a patient math tutor. The student answered incorrectly.
In 3-6 sentences: identify the likely mistake given their answer, explain the correct
approach step by step, and state the correct answer. Use LaTeX math in $...$."""


def hint_stream(db: Session, statement_md: str, parts: list[dict], wrong_answers: list[str] | None) -> AsyncIterator[str]:
    prompts = "\n".join(p.get("prompt_md", "") for p in parts)
    user = f"Problem:\n{statement_md}\n{prompts}"
    if wrong_answers:
        user += f"\n\nThe student's incorrect attempt: {wrong_answers}"
    choice = router.resolve(db, JobType.hint)
    return choice.provider.stream(
        [Message("system", HINT_SYSTEM), Message("user", user)], choice.model
    )


def explain_stream(db: Session, statement_md: str, parts: list[dict], user_answers: list[str], canonical: list[str]) -> AsyncIterator[str]:
    prompts = "\n".join(p.get("prompt_md", "") for p in parts)
    user = (
        f"Problem:\n{statement_md}\n{prompts}\n\n"
        f"Student's answer(s): {user_answers}\nCorrect answer(s): {canonical}"
    )
    choice = router.resolve(db, JobType.explain_mistake)
    return choice.provider.stream(
        [Message("system", EXPLAIN_SYSTEM), Message("user", user)], choice.model
    )
