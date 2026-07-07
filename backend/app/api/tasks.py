from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..content import checking
from ..content.generators import REGISTRY, make_instance
from ..db import get_db
from ..engine import scheduler, srs, xp
from ..engine.mastery import get_or_create_state
from ..models import Attempt, Mastery, Task, Topic, UserTopicState
from ..schemas import LessonOut

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

PROFILE_ID = 1
SLOW_MS = 90_000


class TaskOut(BaseModel):
    id: int
    type: str
    status: str
    xp_value: int
    xp_awarded: int
    title: str
    topic_ids: list[int]
    total_problems: int
    done_problems: int


class TodayOut(BaseModel):
    date: str
    daily_goal: int
    xp_today: int
    streak: int
    tasks: list[TaskOut]


def _task_out(db: Session, task: Task) -> TaskOut:
    problems = (task.payload or {}).get("problems", [])
    if task.type == "lesson":
        title = (task.payload or {}).get("title", "Lesson")
    elif task.type == "review":
        title = f"Review · {len(problems)} topics"
    else:
        title = f"Quiz · {len(problems)} questions"
    return TaskOut(
        id=task.id,
        type=task.type,
        status=task.status,
        xp_value=task.xp_value,
        xp_awarded=task.xp_awarded,
        title=title,
        topic_ids=task.topic_ids,
        total_problems=len(problems),
        done_problems=sum(1 for p in problems if p.get("done")),
    )


@router.get("/today", response_model=TodayOut)
def today(db: Session = Depends(get_db)):
    tasks = scheduler.build_today(db, PROFILE_ID)
    _sync_lesson_tasks(db, tasks)
    from datetime import date

    day = date.today().isoformat()
    return TodayOut(
        date=day,
        daily_goal=xp.daily_goal(db),
        xp_today=xp.xp_on(db, PROFILE_ID, day),
        streak=xp.streak(db, PROFILE_ID),
        tasks=[_task_out(db, t) for t in tasks],
    )


def _sync_lesson_tasks(db: Session, tasks: list[Task]) -> None:
    """Lesson tasks complete when their topic reaches learned (via the Learn page)."""
    dirty = False
    for task in tasks:
        if task.type != "lesson" or task.status == "done":
            continue
        state = db.get(UserTopicState, (PROFILE_ID, task.topic_ids[0]))
        if state and state.mastery in (Mastery.learned.value, Mastery.mastered.value):
            task.status = "done"
            task.xp_awarded = task.xp_value
            task.completed_at = datetime.now(timezone.utc)
            dirty = True
    if dirty:
        db.commit()


class TaskProblemOut(BaseModel):
    index: int
    topic_id: int
    topic_title: str
    generator_key: str
    seed: int
    difficulty: int
    statement_md: str
    parts: list[dict]
    done: bool
    correct: bool | None


class TaskDetail(BaseModel):
    id: int
    type: str
    status: str
    xp_value: int
    problems: list[TaskProblemOut]


@router.get("/{task_id}", response_model=TaskDetail)
def task_detail(task_id: int, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(404, "task not found")
    problems = (task.payload or {}).get("problems", [])
    out = []
    for i, p in enumerate(problems):
        topic = db.get(Topic, p["topic_id"])
        inst = make_instance(p["generator_key"], p["seed"], p["difficulty"])
        pub = inst.public_dict()
        out.append(
            TaskProblemOut(
                index=i,
                topic_id=p["topic_id"],
                topic_title=topic.title if topic else "",
                generator_key=p["generator_key"],
                seed=p["seed"],
                difficulty=p["difficulty"],
                statement_md=pub["statement_md"],
                parts=pub["parts"],
                done=bool(p.get("done")),
                correct=p.get("correct"),
            )
        )
    return TaskDetail(
        id=task.id, type=task.type, status=task.status, xp_value=task.xp_value, problems=out
    )


class TaskAttemptIn(BaseModel):
    index: int
    answers: list[str]
    time_ms: int | None = None
    hints_used: int = 0


class TaskAttemptOut(BaseModel):
    correct: bool
    part_results: list[dict]
    solution_md: str
    task_status: str
    task_complete: bool
    xp_awarded: int
    next_index: int | None


@router.post("/{task_id}/attempt", response_model=TaskAttemptOut)
def task_attempt(task_id: int, body: TaskAttemptIn, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(404, "task not found")
    payload = dict(task.payload or {})
    problems = list(payload.get("problems", []))
    if not (0 <= body.index < len(problems)):
        raise HTTPException(400, "bad problem index")
    p = dict(problems[body.index])
    if p.get("done"):
        raise HTTPException(409, "problem already answered")
    if p["generator_key"] not in REGISTRY:
        raise HTTPException(400, "unknown generator")

    inst = make_instance(p["generator_key"], p["seed"], p["difficulty"])
    parts = [
        {
            "prompt_md": pt.prompt_md,
            "answer_type": pt.answer_type,
            "canonical": pt.canonical,
            "tolerance": pt.tolerance,
            "choices": pt.choices,
        }
        for pt in inst.parts
    ]
    correct, part_results = checking.check_instance(parts, body.answers)

    p["done"] = True
    p["correct"] = correct
    problems[body.index] = p
    payload["problems"] = problems
    task.payload = payload

    db.add(
        Attempt(
            profile_id=PROFILE_ID,
            topic_id=p["topic_id"],
            task_id=task.id,
            generator_key=p["generator_key"],
            seed=p["seed"],
            difficulty=p["difficulty"],
            presented=inst.to_dict(),
            user_answer={"answers": body.answers},
            correct=correct,
            part_results=part_results,
            hints_used=body.hints_used,
            time_ms=body.time_ms,
            context=task.type,
        )
    )

    # Feed the FSRS card for this topic.
    state = get_or_create_state(db, PROFILE_ID, p["topic_id"])
    rating = srs.derive_rating(correct, body.hints_used, bool(body.time_ms and body.time_ms > SLOW_MS))
    srs.review(state, rating)

    xp_awarded = 0
    task_complete = all(pr.get("done") for pr in problems)
    if task_complete and task.status != "done":
        task.status = "done"
        task.completed_at = datetime.now(timezone.utc)
        bonus = 0
        if task.type == "quiz":
            accuracy = sum(1 for pr in problems if pr.get("correct")) / len(problems)
            bonus = round(5 * accuracy)
        xp_awarded = task.xp_value + bonus
        task.xp_awarded = xp_awarded
        xp.award(db, PROFILE_ID, xp_awarded, f"{task.type}:{task.id}", task_id=task.id)

    db.commit()

    next_index = next((i for i, pr in enumerate(problems) if not pr.get("done")), None)
    return TaskAttemptOut(
        correct=correct,
        part_results=part_results,
        solution_md=inst.solution_md,
        task_status=task.status,
        task_complete=task_complete,
        xp_awarded=xp_awarded,
        next_index=next_index,
    )
