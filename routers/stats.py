from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from typing import List, Dict, Any
from datetime import datetime, timezone

from models import Task
from database import get_async_session
from schemas import TimingStatsResponse

router = APIRouter(
    prefix="/stats",
    tags=["statistics"]
)


@router.get("/", response_model=dict)
async def get_tasks_stats(db: AsyncSession = Depends(get_async_session)) -> dict:
    # Общее количество задач
    total_result = await db.execute(select(func.count(Task.id)))
    total_tasks = total_result.scalar() or 0

    # Подсчет по квадрантам (одним запросом)
    quadrant_result = await db.execute(
        select(
            Task.quadrant,
            func.count(Task.id).label('count')
        ).group_by(Task.quadrant)
    )
    by_quadrant = {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0}
    for row in quadrant_result:
        # row is a RowMapping or tuple; try to access attributes
        try:
            q = row.quadrant
            c = row.count
        except Exception:
            q, c = row[0], row[1]
        by_quadrant[q] = c

    # Подсчет по статусу (одним запросом)
    status_result = await db.execute(
        select(
            func.count(case((Task.completed == True, 1))).label('completed'),
            func.count(case((Task.completed == False, 1))).label('pending')
        )
    )
    status_row = status_result.one()
    by_status = {
        "completed": status_row.completed or 0,
        "pending": status_row.pending or 0
    }

    return {
        "total_tasks": total_tasks,
        "by_quadrant": by_quadrant,
        "by_status": by_status
    }


@router.get("/deadlines", response_model=List[Dict[str, Any]])
async def get_deadlines_stats(db: AsyncSession = Depends(get_async_session)):
    """
    Получить статистику по срокам выполнения задач со статусом "pending"
    Возвращает: название, описание, дата начала, оставшийся срок (в днях)
    """
    result = await db.execute(
        select(Task).where(Task.completed == False).order_by(Task.deadline_at)
    )
    tasks = result.scalars().all()

    stats = []
    now = datetime.now(timezone.utc)

    for task in tasks:
        days_left = None
        if task.deadline_at:
            # Сравниваем в UTC, учитываем возможный tzinfo
            try:
                deadline_date = task.deadline_at
                if deadline_date.tzinfo is None:
                    # treat as UTC
                    from datetime import timezone as _tz
                    deadline_date = deadline_date.replace(tzinfo=_tz.utc)
                days_left = (deadline_date.date() - now.date()).days
            except Exception:
                days_left = None

        stats.append({
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "created_at": task.created_at.date() if task.created_at else None,
            "deadline_at": task.deadline_at,
            "days_until_deadline": days_left,
            "quadrant": task.quadrant,
            "is_important": task.is_important
        })

    return stats


@router.get("/timing", response_model=TimingStatsResponse)
async def get_deadline_stats(db: AsyncSession = Depends(get_async_session)) -> TimingStatsResponse:
    """
    Возвращает четыре счетчика:
    - completed_on_time: завершенные в срок
    - completed_late: завершенные поздно
    - on_plan_pending: незавершенные с дедлайном в будущем
    - overtime_pending: незавершенные просроченные
    """
    now_utc = datetime.now(timezone.utc)

    statement = select(
        func.sum(
            case(((Task.completed == True) & (Task.completed_at <= Task.deadline_at), 1), else_=0)
        ).label("completed_on_time"),
        func.sum(
            case(((Task.completed == True) & (Task.completed_at > Task.deadline_at), 1), else_=0)
        ).label("completed_late"),
        func.sum(
            case(((Task.completed == False) & (Task.deadline_at != None) & (Task.deadline_at > now_utc), 1), else_=0)
        ).label("on_plan_pending"),
        func.sum(
            case(((Task.completed == False) & (Task.deadline_at != None) & (Task.deadline_at <= now_utc), 1), else_=0)
        ).label("overdue_pending"),
    ).select_from(Task)

    result = await db.execute(statement)
    stats_row = result.one()

    return TimingStatsResponse(
        completed_on_time=stats_row.completed_on_time or 0,
        completed_late=stats_row.completed_late or 0,
        on_plan_pending=stats_row.on_plan_pending or 0,
        overtime_pending=stats_row.overdue_pending or 0,
    )