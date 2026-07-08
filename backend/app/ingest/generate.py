"""Stage 4: LLM writes a lesson and practice problems per derived topic,
with a verification gate — every answer must at least parse, and unverifiable
problems are flagged and kept out of grading contexts."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..content import checking
from ..content.llm_content import LESSON_SCHEMA, LESSON_SYSTEM
from ..llm import router
from ..llm.base import JobType, Message
from ..llm.cache import cached_complete_json
from ..models import Document, DocumentSection, Lesson, Problem, Topic

PROBLEMS_SCHEMA = {
    "type": "object",
    "properties": {
        "problems": {
            "type": "array",
            "minItems": 3,
            "maxItems": 6,
            "items": {
                "type": "object",
                "properties": {
                    "statement_md": {"type": "string"},
                    "parts": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 3,
                        "items": {
                            "type": "object",
                            "properties": {
                                "prompt_md": {"type": "string"},
                                "answer_type": {
                                    "type": "string",
                                    "enum": ["numeric", "expression", "multiple_choice", "exact_string"],
                                },
                                "canonical": {"type": "string"},
                                "choices": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["prompt_md", "answer_type", "canonical"],
                        },
                    },
                    "solution_md": {"type": "string"},
                    "difficulty": {"type": "integer"},
                },
                "required": ["statement_md", "parts", "solution_md", "difficulty"],
            },
        }
    },
    "required": ["problems"],
}

PROBLEMS_SYSTEM = """You write practice problems for one specific math topic in a
mastery-based learning app. Requirements:
- Each problem tests THIS topic, with difficulty 1 (routine) to 3 (stretch).
- Use Markdown with $...$ LaTeX math.
- answer_type "numeric": canonical is a plain number like "42", "-2.5" or "3/4".
- answer_type "expression": canonical is a sympy-parseable expression like "7*x + 2"
  (variables x, y only).
- answer_type "multiple_choice": provide 3-4 choices; canonical is the INDEX
  (as a string, e.g. "0") of the correct choice; distractors reflect real mistakes.
- Every canonical answer must be exactly correct — double-check the arithmetic.
- solution_md walks through the reasoning in 2-4 sentences."""


def verify_problem(parts: list[dict]) -> bool:
    """Static verification: every canonical answer must parse for its type."""
    for p in parts:
        t = p.get("answer_type")
        canonical = str(p.get("canonical", ""))
        if t == "numeric":
            if checking.parse_number(canonical) is None:
                return False
        elif t == "expression":
            if checking.sanitize_expression(canonical) is None:
                return False
            if checking.preview_latex(canonical) is None:
                return False
        elif t == "multiple_choice":
            choices = p.get("choices") or []
            if not canonical.isdigit() or not (0 <= int(canonical) < len(choices)):
                return False
        elif t == "exact_string":
            if not canonical.strip():
                return False
        else:
            return False
    return True


async def generate_content(db: Session, doc: Document, progress=None) -> None:
    topics = db.scalars(
        select(Topic)
        .join(DocumentSection, Topic.document_section_id == DocumentSection.id)
        .where(DocumentSection.document_id == doc.id)
        .order_by(Topic.id)
    ).all()

    for i, topic in enumerate(topics):
        section = db.get(DocumentSection, topic.document_section_id)
        excerpt = (section.text if section else "")[:8000]

        has_lesson = db.scalar(select(Lesson).where(Lesson.topic_id == topic.id)) is not None
        if not has_lesson:
            choice = router.resolve(db, JobType.ingest_lesson)
            result = await cached_complete_json(
                db,
                choice,
                JobType.ingest_lesson,
                [
                    Message("system", LESSON_SYSTEM),
                    Message(
                        "user",
                        f"Write the lesson.\n\nTopic: {topic.title}\nScope: {topic.description}\n\n"
                        f"Ground the lesson in this source material (do not quote it verbatim):\n{excerpt}",
                    ),
                ],
                LESSON_SCHEMA,
            )
            examples = [
                ex
                for ex in (result.get("worked_examples") or [])
                if isinstance(ex, dict) and ex.get("problem_md") and ex.get("solution_md")
            ]
            db.add(
                Lesson(
                    topic_id=topic.id,
                    content_md=str(result.get("content_md") or ""),
                    worked_examples=examples,
                    source="document",
                    model=f"{choice.provider_name}:{choice.model}",
                    review_status="draft",
                )
            )
            db.commit()

        has_problems = db.scalar(select(Problem).where(Problem.topic_id == topic.id)) is not None
        if not has_problems:
            choice = router.resolve(db, JobType.ingest_problems)
            result = await cached_complete_json(
                db,
                choice,
                JobType.ingest_problems,
                [
                    Message("system", PROBLEMS_SYSTEM),
                    Message(
                        "user",
                        f"Topic: {topic.title}\nScope: {topic.description}\n\n"
                        f"Source material for grounding:\n{excerpt[:4000]}",
                    ),
                ],
                PROBLEMS_SCHEMA,
            )
            for pdoc in result.get("problems", []):
                # Local models sometimes emit malformed entries (a bare string,
                # missing parts, non-list parts). Skip them rather than crash
                # the whole book's ingestion.
                if not isinstance(pdoc, dict) or not pdoc.get("statement_md"):
                    continue
                parts = pdoc.get("parts")
                if not isinstance(parts, list):
                    continue
                parts = [p for p in parts if isinstance(p, dict) and p.get("canonical") is not None]
                if not parts:
                    continue
                try:
                    difficulty = max(1, min(3, int(pdoc.get("difficulty", 1))))
                except (TypeError, ValueError):
                    difficulty = 1
                db.add(
                    Problem(
                        topic_id=topic.id,
                        statement_md=str(pdoc["statement_md"]),
                        parts=parts,
                        solution_md=str(pdoc.get("solution_md", "")),
                        difficulty=difficulty,
                        answer_verified=verify_problem(parts),
                        source="document",
                        model=f"{choice.provider_name}:{choice.model}",
                        review_status="draft",
                    )
                )
            db.commit()

        if progress:
            progress("generating lessons & problems", i + 1, len(topics), topic.title)
