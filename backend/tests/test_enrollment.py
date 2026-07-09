import pytest
from fastapi.testclient import TestClient

from app.db import get_db
from app.engine import diagnostic as diag
from app.engine.graph import TopicGraph
from app.main import app


@pytest.fixture()
def client(seeded_db):
    def override_db():
        yield seeded_db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_enroll_and_unenroll(client):
    courses = client.get("/api/courses").json()
    slug = courses[0]["slug"]
    assert courses[0]["enrolled"] is False

    res = client.put(f"/api/courses/{slug}/enroll")
    assert res.status_code == 200 and res.json()["enrolled"] is True
    # Enrolling is idempotent.
    assert client.put(f"/api/courses/{slug}/enroll").json()["enrolled"] is True
    assert next(c for c in client.get("/api/courses").json() if c["slug"] == slug)["enrolled"]

    res = client.delete(f"/api/courses/{slug}/enroll")
    assert res.status_code == 200 and res.json()["enrolled"] is False


def test_enrollment_gates_today_lessons(client):
    assert not any(t["type"] == "lesson" for t in client.get("/api/tasks/today").json()["tasks"])
    # Enrolling in the root course surfaces its frontier lesson.
    slug = client.get("/api/courses").json()[0]["slug"]
    client.put(f"/api/courses/{slug}/enroll")
    tasks = client.get("/api/tasks/today").json()["tasks"]
    assert any(t["type"] == "lesson" for t in tasks)


def test_starting_placement_enrolls(client):
    slug = client.get("/api/courses").json()[0]["slug"]
    res = client.post("/api/diagnostic/start", json={"course_slugs": [slug]})
    assert res.status_code == 200
    assert next(c for c in client.get("/api/courses").json() if c["slug"] == slug)["enrolled"]


def test_failed_placement_suggests_earlier_material(seeded_db):
    graph = TopicGraph.load(seeded_db)
    session = diag.start_session(seeded_db, 1, ["foundations-i"], graph)
    assert session.belief, "course should have probeable topics"

    # Miss every probe.
    for _ in range(diag.MAX_QUESTIONS):
        tid = diag.next_probe(session, graph)
        if tid is None:
            break
        diag.record_answer(seeded_db, session, graph, tid, correct=False)

    result = diag.finish(seeded_db, session, graph)
    assert result["placed_mastered"] == 0
    assert result["failed_placement"] is True
    assert result["suggested_earlier"], "should point at earlier/prerequisite courses"
    assert all("slug" in s and "title" in s for s in result["suggested_earlier"])
