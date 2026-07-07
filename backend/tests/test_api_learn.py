import pytest
from fastapi.testclient import TestClient

from app.content.generators import make_instance
from app.db import get_db
from app.main import app


@pytest.fixture()
def client(seeded_db):
    def override_db():
        yield seeded_db

    app.dependency_overrides[get_db] = override_db
    # No lifespan: tables/seed come from the seeded_db fixture.
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def canonical_answers(problem: dict) -> list[str]:
    inst = make_instance(problem["generator_key"], problem["seed"], problem["difficulty"])
    answers = []
    for p in inst.parts:
        if p.answer_type == "expression":
            answers.append(p.canonical.replace("*", ""))
        else:
            answers.append(p.canonical)
    return answers


def topic_id_for(client: TestClient, slug: str) -> int:
    course = client.get("/api/courses/foundations-i").json()
    for unit in course["units"]:
        for t in unit["topics"]:
            if t["slug"] == slug:
                return t["id"]
    raise AssertionError(f"topic {slug} not found")


def test_locked_topic_rejected(client):
    tid = topic_id_for(client, "two-step-equations")
    assert client.get(f"/api/learn/{tid}").status_code == 409


def test_complete_lesson_end_to_end(client):
    tid = topic_id_for(client, "place-value")
    state = client.get(f"/api/learn/{tid}").json()
    assert state["mastery"] == "unlocked"
    assert state["lesson"] is not None
    problem = state["problem"]

    completed = False
    xp = 0
    for _ in range(12):  # 6 correct answers should complete (2 per tier × 3 tiers)
        out = client.post(
            f"/api/learn/{tid}/attempt",
            json={
                "generator_key": problem["generator_key"],
                "seed": problem["seed"],
                "difficulty": problem["difficulty"],
                "answers": canonical_answers(problem),
            },
        ).json()
        assert out["correct"], out
        xp += out["xp_awarded"]
        if out["events"]["lesson_complete"]:
            completed = True
            break
        problem = out["next_problem"]

    assert completed
    assert xp > 0
    assert out["mastery"] == "learned"

    # Completing the root topic unlocks its dependents.
    course = client.get("/api/courses/foundations-i").json()
    by_slug = {t["slug"]: t for u in course["units"] for t in u["topics"]}
    assert by_slug["place-value"]["mastery"] == "learned"
    assert by_slug["whole-add-sub"]["mastery"] == "unlocked"
    assert by_slug["whole-multiply"]["mastery"] == "locked"


def test_wrong_answer_reveals_solution_and_resets(client):
    tid = topic_id_for(client, "place-value")
    state = client.get(f"/api/learn/{tid}").json()
    problem = state["problem"]
    out = client.post(
        f"/api/learn/{tid}/attempt",
        json={
            "generator_key": problem["generator_key"],
            "seed": problem["seed"],
            "difficulty": problem["difficulty"],
            "answers": ["999999883" for _ in problem["parts"]],
        },
    ).json()
    assert not out["correct"]
    assert out["solution_md"]
    assert out["progress"]["streak"] == 0
    assert out["next_problem"] is not None


def test_expression_preview(client):
    out = client.get("/api/learn/preview/expression", params={"expr": "3x + 1/2"}).json()
    assert out["ok"] and "frac" in out["latex"]
    bad = client.get("/api/learn/preview/expression", params={"expr": "import os"}).json()
    assert not bad["ok"]
