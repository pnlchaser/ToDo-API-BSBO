from fastapi import APIRouter, HTTPException, Depends, Query, status

from typing import List, Optional
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from schemas import TaskCreate, TaskUpdate, TaskResponse
from models import Task, User, UserRole
from database import get_async_session
from utils import calculate_urgency, calculate_days_until_deadline, determine_quadrant
from dependencies import get_current_user

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    responses={404: {"description": "Task not found"}},
)

# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ вынесены в `utils.py`

def task_to_response(task: Task) -> TaskResponse:
    """Конвертирует SQLAlchemy модель в Pydantic схему (вычисляемые поля будут добавлены схемой)."""
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        is_important=task.is_important,
        deadline_at=task.deadline_at,
        quadrant=task.quadrant,
        completed=task.completed,
        created_at=task.created_at,
    )

# GET ВСЕ ЗАДАЧИ
@router.get("/", response_model=List[TaskResponse])
async def get_all_tasks(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    # Admins see all tasks; regular users see only their tasks
    if current_user.role == UserRole.ADMIN:
        result = await db.execute(select(Task))
    else:
        result = await db.execute(select(Task).where(Task.user_id == current_user.id))
    tasks = result.scalars().all()
    return [task_to_response(task) for task in tasks]


# GET ЗАДАЧИ ПО КВАДРАНТУ
@router.get("/quadrant/{quadrant}", response_model=List[TaskResponse])
async def get_tasks_by_quadrant(
    quadrant: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    if quadrant not in ["Q1", "Q2", "Q3", "Q4"]:
        raise HTTPException(status_code=400, detail="Неверный квадрант. Используйте: Q1, Q2, Q3, Q4")
    
    if current_user.role == UserRole.ADMIN:
        result = await db.execute(select(Task).where(Task.quadrant == quadrant))
    else:
        result = await db.execute(
            select(Task).where((Task.quadrant == quadrant) & (Task.user_id == current_user.id))
        )
    tasks = result.scalars().all()
    return [task_to_response(task) for task in tasks]

# ПОИСК ЗАДАЧ
@router.get("/search", response_model=List[TaskResponse])
async def search_tasks(
    q: str = Query(..., min_length=2),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    keyword = f"%{q.lower()}%"
    stmt = select(Task).where(
        (Task.title.ilike(keyword)) | (Task.description.ilike(keyword))
    )
    if current_user.role != UserRole.ADMIN:
        stmt = stmt.where(Task.user_id == current_user.id)
    result = await db.execute(stmt)
    tasks = result.scalars().all()
    
    if not tasks:
        raise HTTPException(status_code=404, detail="По данному запросу ничего не найдено")
    
    return [task_to_response(task) for task in tasks]


# GET ЗАДАЧИ, срок которых истекает сегодня
@router.get("/today", response_model=List[TaskResponse])
async def get_tasks_due_today(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Возвращает задачи, у которых дедлайн — сегодня (по дате)."""
    today = date.today()
    stmt = select(Task).where(func.date(Task.deadline_at) == today)
    if current_user.role != UserRole.ADMIN:
        stmt = stmt.where(Task.user_id == current_user.id)
    result = await db.execute(stmt)
    tasks = result.scalars().all()
    return [task_to_response(task) for task in tasks]

# GET ЗАДАЧИ ПО СТАТУСУ
@router.get("/status/{status}", response_model=List[TaskResponse])
async def get_tasks_by_status(
    status: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    if status not in ["completed", "pending"]:
        raise HTTPException(status_code=400, detail="Недопустимый статус. Используйте: completed или pending")
    
    is_completed = (status == "completed")
    stmt = select(Task).where(Task.completed == is_completed)
    if current_user.role != UserRole.ADMIN:
        stmt = stmt.where(Task.user_id == current_user.id)
    result = await db.execute(stmt)
    tasks = result.scalars().all()
    return [task_to_response(task) for task in tasks]

# GET ЗАДАЧА ПО ID
@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_by_id(
    task_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    # Если не админ — вернуть только если задача принадлежит текущему пользователю
    if current_user.role != UserRole.ADMIN and task.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    return task_to_response(task)

# POST - СОЗДАНИЕ НОВОЙ ЗАДАЧИ
@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task: TaskCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    # Определяем квадрант на основе важности и дедлайна
    quadrant = determine_quadrant(task.is_important, task.deadline_at)
    # Обновим флаг срочности в модели для консистентности
    is_urgent = calculate_urgency(task.deadline_at)
    
    new_task = Task(
        title=task.title,
        description=task.description,
        is_important=task.is_important,
        is_urgent=is_urgent,
        deadline_at=task.deadline_at,
        quadrant=quadrant,
        completed=False,
        user_id=current_user.id,
    )
    
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    
    return task_to_response(new_task)

# PUT - ОБНОВЛЕНИЕ ЗАДАЧИ
@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    # Находим задачу
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    if current_user.role != UserRole.ADMIN and task.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    # Обновляем только переданные поля
    update_data = task_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(task, field, value)

    # Пересчитываем квадрант/срочность если изменилась важность или дедлайн
    if "is_important" in update_data or "deadline_at" in update_data:
        task.quadrant = determine_quadrant(task.is_important, task.deadline_at)
        task.is_urgent = calculate_urgency(task.deadline_at)

    await db.commit()
    await db.refresh(task)
    
    return task_to_response(task)

# PATCH - ОТМЕТИТЬ ЗАДАЧУ ВЫПОЛНЕННОЙ
@router.patch("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    if current_user.role != UserRole.ADMIN and task.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    task.completed = True
    task.completed_at = datetime.now()

    await db.commit()
    await db.refresh(task)

    return task_to_response(task)

# DELETE - УДАЛЕНИЕ ЗАДАЧИ
@router.delete("/{task_id}", status_code=status.HTTP_200_OK)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    if current_user.role != UserRole.ADMIN and task.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    await db.delete(task)
    await db.commit()

    return {
        "message": "Задача успешно удалена",
        "id": task_id
    }