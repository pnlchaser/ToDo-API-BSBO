from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Dict, Any
from datetime import date

from models import Task
from database import get_async_session
router = APIRouter(
    prefix="/stats",
    tags=["statistics"]
)
@router.get("/", response_model=dict)
async def get_tasks_stats(db: AsyncSession = Depends(get_async_session)) -> dict:
    result = await db.execute(select(Task))
    tasks = result.scalars().all()
    total_tasks = len(tasks)
    by_quadrant = {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0}
    by_status = {"completed": 0, "pending": 0}
    for task in tasks:
        if task.quadrant in by_quadrant:
            by_quadrant[task.quadrant] += 1
        if task.completed:
            by_status["completed"] += 1
        else:
            by_status["pending"] += 1
    return {
        "total_tasks": total_tasks,
        "by_quadrant": by_quadrant,
        "by_status": by_status
    }

#СТАТИСТИКА ПО ДЕДЛАЙНАМ
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
    today = date.today()
    
    for task in tasks:
        days_left = None
        if task.deadline_at:
            # Сравниваем даты без времени
            days_left = (task.deadline_at.date() - today).days
        
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