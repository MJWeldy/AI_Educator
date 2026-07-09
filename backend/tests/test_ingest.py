"""Ingestion pipeline against a synthetic fixture PDF and a fake LLM."""

from pathlib import Path

import fitz
import pytest
from sqlalchemy import select

from app.ingest import extract, segment
from app.ingest.generate import verify_problem
from app.models import Course, Document, DocumentSection, Lesson, Problem, Topic

CHAPTERS = [
    ("Sets and Logic", ["What is a set", "Set operations", "Basic logic"]),
    ("Functions", ["Definition of a function", "Composition", "Inverses"]),
]


@pytest.fixture()
def fixture_pdf(tmp_path):
    path = tmp_path / "book.pdf"
    pdf = fitz.open()
    toc = []
    page_no = 0
    for chapter, sections in CHAPTERS:
        page = pdf.new_page()
        page.insert_text((72, 72), chapter, fontsize=24)
        toc.append([1, chapter, page_no + 1])
        page_no += 1
        for section in sections:
            page = pdf.new_page()
            page.insert_text((72, 72), section, fontsize=16)
            page.insert_text(
                (72, 120),
                f"This section teaches {section.lower()}. " * 30,
                fontsize=11,
            )
            toc.append([2, section, page_no + 1])
            page_no += 1
    pdf.set_toc(toc)
    pdf.save(str(path))
    pdf.close()
    return path


@pytest.fixture()
def doc(db, fixture_pdf, tmp_path, monkeypatch):
    from app import config

    monkeypatch.setattr(config.settings, "extracted_dir", tmp_path / "extracted")
    document = Document(filename="book.pdf", stored_path=str(fixture_pdf), title="Test Book")
    db.add(document)
    db.commit()
    return document


def test_extract(doc):
    result = extract.extract(doc)
    assert result["page_count"] == 8
    assert len(result["toc"]) == 8
    assert "teaches what is a set" in result["pages"][1].lower()
    # cached second run
    again = extract.extract(doc)
    assert again["page_count"] == 8


def test_segment_uses_toc(db, doc):
    extracted = extract.extract(doc)
    sections = segment.build_sections(db, doc, extracted)
    chapters = [s for s in sections if s.level == 1]
    leaves = [s for s in sections if s.level == 2]
    assert len(chapters) == 2
    assert len(leaves) == 6
    assert all(s.parent_id for s in leaves)
    assert any("set operations" in s.title.lower() for s in leaves)
    # checkpoint: second call returns existing rows
    assert len(segment.build_sections(db, doc, extracted)) == len(sections)


def test_segment_without_toc(db, tmp_path):
    path = tmp_path / "plain.pdf"
    pdf = fitz.open()
    for i in range(25):
        page = pdf.new_page()
        page.insert_text((72, 72), f"page {i} content " * 40, fontsize=11)
    pdf.save(str(path))
    pdf.close()
    document = Document(filename="plain.pdf", stored_path=str(path))
    db.add(document)
    db.commit()
    extracted = {"page_count": 25, "toc": [], "pages": [f"page {i}" for i in range(25)]}
    sections = segment.build_sections(db, document, extracted)
    leaves = [s for s in sections if s.level == 2]
    assert len(leaves) == 3  # 25 pages / 10 per chunk


def test_extract_and_segment_multifile(db, tmp_path, monkeypatch):
    from app import config
    from app.ingest import extract as extract_mod
    from app.models import DocumentFile

    monkeypatch.setattr(config.settings, "extracted_dir", tmp_path / "extracted")

    # A small PDF plus a markdown note, uploaded as one "folder".
    pdf_path = tmp_path / "book.pdf"
    pdf = fitz.open()
    for i in range(3):
        pdf.new_page().insert_text((72, 72), f"chapter text page {i} " * 30, fontsize=11)
    pdf.save(str(pdf_path))
    pdf.close()
    md_path = tmp_path / "notes.md"
    md_path.write_text("# My notes\n\nSome markdown about vectors and spaces.\n")

    document = Document(filename="my-folder", stored_path="")
    db.add(document)
    db.flush()
    db.add(DocumentFile(document_id=document.id, filename="my-folder/book.pdf",
                        stored_path=str(pdf_path), position=0, kind="pdf"))
    db.add(DocumentFile(document_id=document.id, filename="my-folder/notes.md",
                        stored_path=str(md_path), position=1, kind="text"))
    db.commit()

    extracted = extract_mod.extract(document)
    assert len(extracted["sources"]) == 2
    assert extracted["page_count"] == 4  # 3 pdf pages + 1 text "page"

    sections = segment.build_sections(db, document, extracted)
    chapters = [s for s in sections if s.level == 1]
    assert {c.title for c in chapters} == {"my-folder/book.pdf", "my-folder/notes.md"}
    # Each file contributes at least one leaf, and the markdown text is captured.
    leaves = [s for s in sections if s.level == 2]
    assert leaves and all(s.parent_id for s in leaves)
    assert any("markdown about vectors" in s.text for s in leaves)


def test_upload_folder_endpoint(db, fixture_pdf, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from app import config
    from app.db import get_db
    from app.main import app
    from app.models import DocumentFile

    monkeypatch.setattr(config.settings, "uploads_dir", tmp_path / "uploads")
    monkeypatch.setattr(config.settings, "extracted_dir", tmp_path / "extracted")

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    pdf_bytes = fixture_pdf.read_bytes()
    try:
        with TestClient(app) as client:
            res = client.post(
                "/api/documents",
                files=[
                    ("files", ("mybook/intro.md", b"# Intro\n\nVectors and spaces.\n", "text/markdown")),
                    ("files", ("mybook/text.pdf", pdf_bytes, "application/pdf")),
                    ("files", ("mybook/skip.bin", b"\x00\x01", "application/octet-stream")),
                ],
            )
            assert res.status_code == 200
            doc_id = res.json()["id"]
            # Folder name becomes the label; unsupported .bin is skipped.
            assert res.json()["filename"] == "mybook"
    finally:
        app.dependency_overrides.clear()

    doc = db.get(Document, doc_id)
    files = db.scalars(select(DocumentFile).where(DocumentFile.document_id == doc_id)).all()
    assert len(files) == 2 and {f.kind for f in files} == {"pdf", "text"}
    for f in files:
        assert Path(f.stored_path).exists()

    extracted = extract.extract(doc)
    sections = segment.build_sections(db, doc, extracted)
    chapters = [s for s in sections if s.level == 1]
    assert {c.title for c in chapters} == {"mybook/intro.md", "mybook/text.pdf"}


def test_verify_problem():
    good_numeric = [{"answer_type": "numeric", "canonical": "3/4", "prompt_md": "x"}]
    assert verify_problem(good_numeric)
    assert not verify_problem([{"answer_type": "numeric", "canonical": "banana"}])
    assert verify_problem(
        [{"answer_type": "expression", "canonical": "2*x + 1", "prompt_md": "x"}]
    )
    assert not verify_problem([{"answer_type": "expression", "canonical": "import os"}])
    assert verify_problem(
        [{"answer_type": "multiple_choice", "canonical": "1", "choices": ["a", "b", "c"]}]
    )
    assert not verify_problem(
        [{"answer_type": "multiple_choice", "canonical": "7", "choices": ["a", "b"]}]
    )


async def test_derive_and_generate_with_fake_llm(seeded_db, doc, monkeypatch):
    from app.ingest import derive, generate

    topics_payload = {
        "topics": [
            {"title": "Union and intersection", "description": "Combining sets", "est_minutes": 10}
        ]
    }
    edges_payload = {"edges": [{"topic": 0, "requires": [], "requires_seed": []}]}
    lesson_payload = {
        "content_md": "Sets combine via union $A \\cup B$.",
        "worked_examples": [
            {"problem_md": "p", "solution_md": "s"},
            {"problem_md": "p2", "solution_md": "s2"},
        ],
    }
    problems_payload = {
        "problems": [
            {
                "statement_md": "What is $|\\{1,2\\} \\cup \\{2,3\\}|$?",
                "parts": [{"prompt_md": "Count:", "answer_type": "numeric", "canonical": "3"}],
                "solution_md": "Union has elements 1,2,3.",
                "difficulty": 1,
            },
            {
                "statement_md": "Broken one",
                "parts": [{"prompt_md": "x", "answer_type": "numeric", "canonical": "not-a-number"}],
                "solution_md": "",
                "difficulty": 1,
            },
        ]
    }

    async def fake_cached(db_, choice, job_type, messages, schema, max_tokens=4096):
        from app.llm.base import JobType

        return {
            JobType.ingest_topics: topics_payload,
            JobType.topic_mapping: edges_payload,
            JobType.ingest_lesson: lesson_payload,
            JobType.ingest_problems: problems_payload,
        }[job_type]

    class FakeChoice:
        provider_name = "fake"
        model = "fake"

    monkeypatch.setattr(derive, "cached_complete_json", fake_cached)
    monkeypatch.setattr(generate, "cached_complete_json", fake_cached)
    monkeypatch.setattr(derive.router, "resolve", lambda d, j: FakeChoice())
    monkeypatch.setattr(generate.router, "resolve", lambda d, j: FakeChoice())

    extracted = extract.extract(doc)
    segment.build_sections(seeded_db, doc, extracted)
    course = await derive.derive_topics(seeded_db, doc)
    assert course.source == "document"

    topics = seeded_db.scalars(select(Topic).where(Topic.course_id == course.id)).all()
    assert topics and all(t.status == "draft" for t in topics)

    # Each document topic gets a grounded reading pointing back at its section.
    from app.ingest.readings import attach_readings
    from app.models import Resource

    added = attach_readings(seeded_db, doc)
    assert added == len(topics)
    assert attach_readings(seeded_db, doc) == 0  # idempotent — no duplicates
    for t in topics:
        reading = seeded_db.scalar(
            select(Resource).where(Resource.topic_id == t.id, Resource.kind == "reading")
        )
        assert reading is not None and reading.title

    await generate.generate_content(seeded_db, doc)
    for t in topics:
        lesson = seeded_db.scalar(select(Lesson).where(Lesson.topic_id == t.id))
        assert lesson is not None and lesson.review_status == "draft"
        problems = seeded_db.scalars(select(Problem).where(Problem.topic_id == t.id)).all()
        assert problems
        verified = [p for p in problems if p.answer_verified]
        unverified = [p for p in problems if not p.answer_verified]
        assert verified and unverified, "verification gate must separate good from broken"

    # Draft topics stay invisible to the learner-facing graph.
    from app.engine.graph import TopicGraph

    graph = TopicGraph.load(seeded_db)
    assert all(t.id not in graph.topics for t in topics)


async def test_delete_document_removes_everything(seeded_db, doc, monkeypatch):
    """Full cleanup: course, topics, content, edges, progress, sections."""
    from fastapi.testclient import TestClient

    from app.db import get_db
    from app.engine.mastery import get_or_create_state
    from app.main import app
    from app.models import Attempt, Course, TopicEdge, UserTopicState

    # Reuse the fake-LLM ingestion from the test above to build a course.
    from app.ingest import derive, generate

    topics_payload = {"topics": [{"title": "Advanced place value drills", "description": "d", "est_minutes": 10}]}
    edges_payload = {"edges": [{"topic": 0, "requires": [], "requires_seed": ["place-value"]}]}
    lesson_payload = {"content_md": "x", "worked_examples": [{"problem_md": "p", "solution_md": "s"}] * 2}
    problems_payload = {"problems": [{
        "statement_md": "1+1?", "parts": [{"prompt_md": "x", "answer_type": "numeric", "canonical": "2"}],
        "solution_md": "", "difficulty": 1}]}

    async def fake_cached(db_, choice, job_type, messages, schema, max_tokens=4096):
        from app.llm.base import JobType
        return {JobType.ingest_topics: topics_payload, JobType.topic_mapping: edges_payload,
                JobType.ingest_lesson: lesson_payload, JobType.ingest_problems: problems_payload}[job_type]

    class FakeChoice:
        provider_name = model = "fake"

    monkeypatch.setattr(derive, "cached_complete_json", fake_cached)
    monkeypatch.setattr(generate, "cached_complete_json", fake_cached)
    monkeypatch.setattr(derive.router, "resolve", lambda d, j: FakeChoice())
    monkeypatch.setattr(generate.router, "resolve", lambda d, j: FakeChoice())

    from app.ingest import extract, segment
    extracted = extract.extract(doc)
    segment.build_sections(seeded_db, doc, extracted)
    course = await derive.derive_topics(seeded_db, doc)
    await generate.generate_content(seeded_db, doc)

    # Seed-weld edges from uploads must be soft (they must not lock the book).
    topic = seeded_db.scalar(select(Topic).where(Topic.course_id == course.id))
    weld = seeded_db.scalar(select(TopicEdge).where(TopicEdge.topic_id == topic.id))
    assert weld is not None and weld.kind == "soft"

    # Simulate some progress on a book topic.
    get_or_create_state(seeded_db, 1, topic.id)
    seeded_db.add(Attempt(profile_id=1, topic_id=topic.id, presented={}, user_answer={}))
    seeded_db.commit()

    def override_db():
        yield seeded_db

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            # Uploaded courses can be renamed (and the document title follows).
            res = client.patch(f"/api/courses/{course.slug}", json={"title": "My Paper"})
            assert res.status_code == 200 and res.json()["title"] == "My Paper"
            assert seeded_db.get(Document, doc.id).title == "My Paper"
            # ...and categorized, without disturbing the title.
            res = client.patch(f"/api/courses/{course.slug}", json={"category": "Ecology"})
            assert res.status_code == 200
            assert res.json()["category"] == "Ecology" and res.json()["title"] == "My Paper"
            # Built-in (seed) courses are managed by the curriculum, not editable here.
            seed_slug = seeded_db.scalar(select(Course.slug).where(Course.source == "seed"))
            assert client.patch(f"/api/courses/{seed_slug}", json={"category": "X"}).status_code == 409
            assert client.delete(f"/api/documents/{doc.id}").status_code == 200
    finally:
        app.dependency_overrides.clear()

    assert seeded_db.scalar(select(Course).where(Course.id == course.id)) is None
    assert seeded_db.scalars(select(Topic).where(Topic.course_id == course.id)).all() == []
    assert seeded_db.scalars(select(DocumentSection).where(DocumentSection.document_id == doc.id)).all() == []
    assert seeded_db.get(Document, doc.id) is None
    assert seeded_db.scalars(select(UserTopicState).where(UserTopicState.topic_id == topic.id)).all() == []


async def test_generate_tolerates_malformed_llm_output(seeded_db, doc, monkeypatch):
    """A local model can emit a bare string, missing parts, or bad difficulty
    inside the problems/topics lists — ingestion must skip them, not crash."""
    from app.ingest import derive, generate

    topics_payload = {"topics": [
        {"title": "Good Topic", "description": "d", "est_minutes": 10},
        "a bare string instead of an object",       # malformed
        {"description": "no title", "est_minutes": 5},  # missing title
        {"title": "Bad Minutes", "est_minutes": "lots"},  # bad est_minutes
    ]}
    edges_payload = {"edges": ["nonsense", {"topic": 0, "requires": [None], "requires_seed": []}]}
    lesson_payload = {"content_md": "ok", "worked_examples": [
        {"problem_md": "p", "solution_md": "s"}, "bad", {"problem_md": "only prompt"},
    ]}
    problems_payload = {"problems": [
        {"statement_md": "Q1", "parts": [{"prompt_md": "x", "answer_type": "numeric", "canonical": "2"}],
         "solution_md": "", "difficulty": 1},
        "a bare string",                              # the crash from the field report
        {"statement_md": "no parts"},                 # missing parts
        {"statement_md": "Q4", "parts": "not a list"},  # parts wrong type
        {"statement_md": "Q5", "parts": [{"prompt_md": "x", "answer_type": "numeric"}]},  # no canonical
    ]}

    async def fake_cached(db_, choice, job_type, messages, schema, max_tokens=4096):
        from app.llm.base import JobType
        return {JobType.ingest_topics: topics_payload, JobType.topic_mapping: edges_payload,
                JobType.ingest_lesson: lesson_payload, JobType.ingest_problems: problems_payload}[job_type]

    class FakeChoice:
        provider_name = model = "fake"

    monkeypatch.setattr(derive, "cached_complete_json", fake_cached)
    monkeypatch.setattr(generate, "cached_complete_json", fake_cached)
    monkeypatch.setattr(derive.router, "resolve", lambda d, j: FakeChoice())
    monkeypatch.setattr(generate.router, "resolve", lambda d, j: FakeChoice())

    extracted = extract.extract(doc)
    segment.build_sections(seeded_db, doc, extracted)
    course = await derive.derive_topics(seeded_db, doc)   # must not raise
    await generate.generate_content(seeded_db, doc)       # must not raise

    topics = seeded_db.scalars(select(Topic).where(Topic.course_id == course.id)).all()
    titles = {t.title for t in topics}
    assert "Good Topic" in titles and "Bad Minutes" in titles
    assert not any(t.title == "no title" for t in topics)

    good = seeded_db.scalar(select(Topic).where(Topic.title == "Good Topic"))
    problems = seeded_db.scalars(select(Problem).where(Problem.topic_id == good.id)).all()
    # Only the one well-formed problem survives the filter.
    assert len(problems) == 1 and problems[0].statement_md == "Q1"
    lesson = seeded_db.scalar(select(Lesson).where(Lesson.topic_id == good.id))
    assert len(lesson.worked_examples) == 1  # the two malformed examples dropped
