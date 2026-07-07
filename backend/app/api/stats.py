from datetime import date, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from .deps import current_profile_id
from ..engine import xp
from ..engine.graph import TopicGraph, effective_masteries
from ..models import Attempt

router = APIRouter(prefix="/api/stats", tags=["stats"])


class StatsOut(BaseModel):
    total_xp: int
    xp_today: int
    daily_goal: int
    streak: int
    mastery_counts: dict[str, int]
    xp_by_day: list[dict]  # [{date, xp}] most recent 30 days
    attempts_total: int
    attempts_correct: int


@router.get("", response_model=StatsOut)
def stats(db: Session = Depends(get_db), profile_id: int = Depends(current_profile_id)):
    days = xp.xp_by_day(db, profile_id)
    today = date.today()
    series = []
    for i in range(29, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        series.append({"date": d, "xp": days.get(d, 0)})

    graph = TopicGraph.load(db)
    masteries = effective_masteries(db, graph, profile_id)
    counts: dict[str, int] = {}
    for m in masteries.values():
        counts[m] = counts.get(m, 0) + 1

    attempts_total = db.scalar(
        select(func.count()).select_from(Attempt).where(Attempt.profile_id == profile_id)
    ) or 0
    attempts_correct = db.scalar(
        select(func.count())
        .select_from(Attempt)
        .where(Attempt.profile_id == profile_id, Attempt.correct.is_(True))
    ) or 0

    return StatsOut(
        total_xp=sum(days.values()),
        xp_today=days.get(today.isoformat(), 0),
        daily_goal=xp.daily_goal(db),
        streak=xp.streak(db, profile_id),
        mastery_counts=counts,
        xp_by_day=series,
        attempts_total=attempts_total,
        attempts_correct=attempts_correct,
    )
