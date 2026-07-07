from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import SettingRow, XpEntry

REVIEW_XP = 4
QUIZ_XP = 15
DEFAULT_DAILY_GOAL = 30


def award(db: Session, profile_id: int, amount: int, reason: str, task_id: int | None = None) -> None:
    db.add(
        XpEntry(
            profile_id=profile_id,
            amount=amount,
            reason=reason,
            task_id=task_id,
            for_date=date.today().isoformat(),
        )
    )


def daily_goal(db: Session) -> int:
    row = db.get(SettingRow, "goal.daily_xp")
    if row and isinstance(row.value, int) and row.value > 0:
        return row.value
    return DEFAULT_DAILY_GOAL


def xp_on(db: Session, profile_id: int, day: str) -> int:
    return (
        db.scalar(
            select(func.coalesce(func.sum(XpEntry.amount), 0)).where(
                XpEntry.profile_id == profile_id, XpEntry.for_date == day
            )
        )
        or 0
    )


def xp_by_day(db: Session, profile_id: int) -> dict[str, int]:
    rows = db.execute(
        select(XpEntry.for_date, func.sum(XpEntry.amount))
        .where(XpEntry.profile_id == profile_id)
        .group_by(XpEntry.for_date)
    ).all()
    return {day: total for day, total in rows}


def streak(db: Session, profile_id: int) -> int:
    """Consecutive days (ending today or yesterday) that met the daily goal."""
    goal = daily_goal(db)
    days = xp_by_day(db, profile_id)
    from datetime import timedelta

    today = date.today()
    count = 0
    cursor = today
    if days.get(cursor.isoformat(), 0) < goal:
        cursor = today - timedelta(days=1)  # today isn't over yet
    while days.get(cursor.isoformat(), 0) >= goal:
        count += 1
        cursor -= timedelta(days=1)
    return count
