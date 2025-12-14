from fastapi import APIRouter, HTTPException, Depends, Query, status

from typing import List, Optional
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from schemas import TaskCreate, TaskUpdate, TaskResponse
from models import Task
from database import get_async_session

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    responses={404: {"description": "Task not found"}},
)

# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
def calculate_urgency(deadline: Optional[datetime]) -> bool:
    """Определяет срочность: True если до дедлайна <= 3 дня"""
    if not deadline:
        return False
    # Преобразуем datetime в date для сравнения
    deadline_date = deadline.date() if isinstance(deadline, datetime) else deadline
    today = date.today()
    days_left = (deadline_date - today).days
    return days_left <= 3

def determine_quadrant(is_important: bool, deadline: Optional[datetime]) -> str:
    """Определяет квадрант на основе важности и дедлайна"""
    is_urgent = calculate_urgency(deadline)
    
    if is_important and is_urgent:
        return "Q1"
    elif is_important and not is_urgent:
        return "Q2"
    elif not is_important and is_urgent:
        return "Q3"
    else:
        return "Q4"

def calculate_days_until_deadline(deadline: Optional[datetime]) -> Optional[int]:
    """Рассчитывает дни до дедлайна"""
    if not deadline:
        return None
    # Преобразуем datetime в date для сравнения
    deadline_date = deadline.date() if isinstance(deadline, datetime) else deadline
    today = date.today()
    return (deadline_date - today).days

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
async def get_all_tasks(db: AsyncSession = Depends(get_async_session)):
    result = await db.execute(select(Task))
    tasks = result.scalars().all()
    return [task_to_response(task) for task in tasks]


# GET ЗАДАЧИ ПО КВАДРАНТУ
@router.get("/quadrant/{quadrant}", response_model=List[TaskResponse])
async def get_tasks_by_quadrant(
    quadrant: str,
    db: AsyncSession = Depends(get_async_session)
):
    if quadrant not in ["Q1", "Q2", "Q3", "Q4"]:
        raise HTTPException(status_code=400, detail="Неверный квадрант. Используйте: Q1, Q2, Q3, Q4")
    
    result = await db.execute(select(Task).where(Task.quadrant == quadrant))
    tasks = result.scalars().all()
    return [task_to_response(task) for task in tasks]

# ПОИСК ЗАДАЧ
@router.get("/search", response_model=List[TaskResponse])
async def search_tasks(
    q: str = Query(..., min_length=2),
    db: AsyncSession = Depends(get_async_session)
):
    keyword = f"%{q.lower()}%"
    result = await db.execute(
        select(Task).where(
            (Task.title.ilike(keyword)) |
            (Task.description.ilike(keyword))
        )
    )
    tasks = result.scalars().all()
    
    if not tasks:
        raise HTTPException(status_code=404, detail="По данному запросу ничего не найдено")
    
    return [task_to_response(task) for task in tasks]

# GET ЗАДАЧИ ПО СТАТУСУ
@router.get("/status/{status}", response_model=List[TaskResponse])
async def get_tasks_by_status(
    status: str,
    db: AsyncSession = Depends(get_async_session)
):
    if status not in ["completed", "pending"]:
        raise HTTPException(status_code=400, detail="Недопустимый статус. Используйте: completed или pending")
    
    is_completed = (status == "completed")
    result = await db.execute(select(Task).where(Task.completed == is_completed))
    tasks = result.scalars().all()
    return [task_to_response(task) for task in tasks]

# GET ЗАДАЧА ПО ID
@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_by_id(
    task_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()



    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    return task_to_response(task)

# POST - СОЗДАНИЕ НОВОЙ ЗАДАЧИ
@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task: TaskCreate,
    db: AsyncSession = Depends(get_async_session)
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
        completed=False
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
    db: AsyncSession = Depends(get_async_session)
):
    # Находим задачу
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
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
    db: AsyncSession = Depends(get_async_session)
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
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
    db: AsyncSession = Depends(get_async_session)
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    await db.delete(task)
    await db.commit()

    return {
        "message": "Задача успешно удалена",
        "id": task_id
    }