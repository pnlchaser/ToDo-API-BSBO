from fastapi import APIRouter, HTTPException, status, Response
from typing import Optional
from datetime import datetime
from schemas import TaskBase, TaskCreate, TaskUpdate, TaskResponse
from database import tasks_db

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    responses={404: {"description": "Task not found"}},
)


#GET ENDPOINTS

@router.get("", response_model=list[TaskResponse])
async def get_all_tasks() -> list[TaskResponse]:
    """Получить все задачи"""
    return tasks_db


@router.get("/search", response_model=list[TaskResponse])
async def search_tasks(q: str) -> list[TaskResponse]:
    """Поиск задач по ключевому слову"""
    if len(q) < 2:
        raise HTTPException(
            status_code=422,
            detail="Ключевое слово должно содержать минимум 2 символа"
        )
    
    q_lower = q.lower()
    found_tasks = [
        task for task in tasks_db
        if q_lower in task["title"].lower() or 
           (task["description"] and q_lower in task["description"].lower())
    ]
    
    if not found_tasks:
        raise HTTPException(
            status_code=404,
            detail=f"Задачи по запросу '{q}' не найдены"
        )
    
    return found_tasks


@router.get("/status/{status}", response_model=list[TaskResponse])
async def get_tasks_by_status(status: str) -> list[TaskResponse]:
    """Фильтрация задач по статусу"""
    if status not in ["completed", "pending"]:
        raise HTTPException(
            status_code=400,
            detail="Неверный статус. Используйте: completed или pending"
        )
    
    is_completed = (status == "completed")
    filtered_tasks = [
        task for task in tasks_db
        if task["completed"] == is_completed
    ]
    
    return filtered_tasks


@router.get("/quadrant/{quadrant}", response_model=list[TaskResponse])
async def get_tasks_by_quadrant(quadrant: str) -> list[TaskResponse]:
    """Фильтрация задач по квадранту"""
    if quadrant not in ["Q1", "Q2", "Q3", "Q4"]:
        raise HTTPException(
            status_code=400,
            detail="Неверный квадрант. Используйте: Q1, Q2, Q3, Q4"
        )
    
    filtered_tasks = [
        task for task in tasks_db
        if task["quadrant"] == quadrant
    ]
    
    return filtered_tasks


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_by_id(task_id: int) -> TaskResponse:
    """Получить задачу по ID"""
    task = next((
        task for task in tasks_db
        if task["id"] == task_id),
        None
    )
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Задача с ID {task_id} не найдена"
        )
    
    return task


# POST ENDPOINT (CREATE)

@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(task: TaskCreate) -> TaskResponse:
    """Создать новую задачу"""
    
    # Определяем квадрант
    if task.is_important and task.is_urgent:
        quadrant = "Q1"
    elif task.is_important and not task.is_urgent:
        quadrant = "Q2"
    elif not task.is_important and task.is_urgent:
        quadrant = "Q3"
    else:
        quadrant = "Q4"
    
    # Генерируем новый ID
    new_id = max([t["id"] for t in tasks_db], default=0) + 1
    
    # Создаем новую задачу
    new_task = {
        "id": new_id,
        "title": task.title,
        "description": task.description,
        "is_important": task.is_important,
        "is_urgent": task.is_urgent,
        "quadrant": quadrant,
        "completed": False,
        "created_at": datetime.now()
    }
    
    # Добавляем в хранилище
    tasks_db.append(new_task)
    
    return new_task


#PUT ENDPOINT (UPDATE)

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: int, task_update: TaskUpdate) -> TaskResponse:
    """Полное обновление задачи"""
    
    # Ищем задачу по ID
    task = next((
        task for task in tasks_db
        if task["id"] == task_id),
        None
    )
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Задача с ID {task_id} не найдена"
        )
    
    # Обновляем только переданные поля
    update_data = task_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        task[field] = value
    
    # Пересчитываем квадрант если изменились важность или срочность
    if "is_important" in update_data or "is_urgent" in update_data:
        if task["is_important"] and task["is_urgent"]:
            task["quadrant"] = "Q1"
        elif task["is_important"] and not task["is_urgent"]:
            task["quadrant"] = "Q2"
        elif not task["is_important"] and task["is_urgent"]:
            task["quadrant"] = "Q3"
        else:
            task["quadrant"] = "Q4"
    
    return task


# PATCH ENDPOINT (PARTIAL UPDATE)

@router.patch("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(task_id: int) -> TaskResponse:
    """Отметить задачу как выполненную"""
    
    task = next((
        task for task in tasks_db
        if task["id"] == task_id),
        None
    )
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Задача с ID {task_id} не найдена"
        )
    
    task["completed"] = True
    task["completed_at"] = datetime.now()
    
    return task


#DELETE ENDPOINT

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int):
    """Удалить задачу по ID"""
    
    task = next((
        task for task in tasks_db
        if task["id"] == task_id),
        None
    )
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Задача с ID {task_id} не найдена"
        )
    
    tasks_db.remove(task)
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)
