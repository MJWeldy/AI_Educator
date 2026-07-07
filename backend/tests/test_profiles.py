import pytest
from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app


@pytest.fixture()
def client(seeded_db):
    def override_db():
        yield seeded_db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def complete_place_value(client: TestClient) -> None:
    from app.content.generators import make_instance

    course = client.get("/api/courses/foundations-i").json()
    tid = next(t["id"] for u in course["units"] for t in u["topics"] if t["slug"] == "place-value")
    problem = client.get(f"/api/learn/{tid}").json()["problem"]
    for _ in range(8):
        inst = make_instance(problem["generator_key"], problem["seed"], problem["difficulty"])
        out = client.post(
            f"/api/learn/{tid}/attempt",
            json={
                "generator_key": problem["generator_key"],
                "seed": problem["seed"],
                "difficulty": problem["difficulty"],
                "answers": [p.canonical for p in inst.parts],
            },
        ).json()
        if out["events"]["lesson_complete"]:
            return
        problem = out["next_problem"]
    raise AssertionError("lesson did not complete")


def test_default_profile_is_one(client):
    data = client.get("/api/profiles").json()
    assert data["current_id"] == 1
    assert data["profiles"][0]["name"] == "Learner"


def test_create_select_and_isolation(client):
    # Profile 1 learns a topic.
    complete_place_value(client)
    assert client.get("/api/stats").json()["mastery_counts"].get("learned", 0) == 1

    # Create and switch to a second profile (cookie set by the API).
    p2 = client.post("/api/profiles", json={"name": "Kid"}).json()
    client.post(f"/api/profiles/{p2['id']}/select")
    assert client.get("/api/profiles").json()["current_id"] == p2["id"]

    # The new profile has fresh progress and its own task queue.
    stats = client.get("/api/stats").json()
    assert stats["mastery_counts"].get("learned", 0) == 0
    assert stats["total_xp"] == 0
    today = client.get("/api/tasks/today").json()
    assert all(t["status"] != "done" for t in today["tasks"])

    # Switching back restores profile 1's progress.
    client.post("/api/profiles/1/select")
    assert client.get("/api/stats").json()["mastery_counts"].get("learned", 0) == 1


def test_tasks_are_profile_scoped(client):
    today = client.get("/api/tasks/today").json()
    task_ids = [t["id"] for t in today["tasks"]]
    assert task_ids

    p2 = client.post("/api/profiles", json={"name": "Other"}).json()
    client.post(f"/api/profiles/{p2['id']}/select")
    # Profile 2 cannot see or answer profile 1's tasks.
    assert client.get(f"/api/tasks/{task_ids[0]}").status_code == 404


def test_delete_profile_and_cleanup(client):
    p2 = client.post("/api/profiles", json={"name": "Temp"}).json()
    client.post(f"/api/profiles/{p2['id']}/select")
    client.get("/api/tasks/today")  # generate some per-profile rows

    res = client.delete(f"/api/profiles/{p2['id']}")
    assert res.status_code == 200
    ids = [p["id"] for p in client.get("/api/profiles").json()["profiles"]]
    assert p2["id"] not in ids
    # Falls back to the default profile after deleting the active one.
    assert client.get("/api/profiles").json()["current_id"] == 1


def test_cannot_delete_last_profile(client):
    assert client.delete("/api/profiles/1").status_code == 409
