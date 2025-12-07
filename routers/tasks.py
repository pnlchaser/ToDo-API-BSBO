from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    responses={404: {"description": "Not found"}}
)

# Временное хранилище задач
tasks_db: List[Dict[str, Any]] = [
    {
        "id": 1,
        "title": "Сдать проект по FastAPI",
        "description": "Завершить разработку API и написать документацию",
        "is_important": True,
        "is_urgent": True,
        "quadrant": "Q1",
        "completed": False,
        "created_at": "2025-12-08T00:00:00"
    },
    {
        "id": 2,
        "title": "Изучить SQLAlchemy",
        "description": "Прочитать документацию и попробовать примеры",
        "is_important": True,
        "is_urgent": False,
        "quadrant": "Q2",
        "completed": False,
        "created_at": "2025-12-08T00:00:00"
    },
    {
        "id": 3,
        "title": "Сходить на лекцию",
        "description": None,
        "is_important": False,
        "is_urgent": True,
        "quadrant": "Q3",
        "completed": False,
        "created_at": "2025-12-08T00:00:00"
    },
    {
        "id": 4,
        "title": "Посмотреть сериал",
        "description": "Новый сезон любимого сериала",
        "is_important": False,
        "is_urgent": False,
        "quadrant": "Q4",
        "completed": True,
        "created_at": "2025-12-08T00:00:00"
    },
]


@router.get("")
async def get_all_tasks() -> dict:
    """Получение списка всех задач"""
    return {
        "count": len(tasks_db),
        "tasks": tasks_db
    }


@router.get("/search")
async def search_tasks(q: str) -> dict:
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
    
    return {
        "query": q,
        "count": len(found_tasks),
        "tasks": found_tasks
    }


@router.get("/status/{status}")
async def get_tasks_by_status(status: str) -> dict:
    """Фильтрация задач по статусу выполнения"""
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
    
    return {
        "status": status,
        "count": len(filtered_tasks),
        "tasks": filtered_tasks
    }


@router.get("/quadrant/{quadrant}")
async def get_tasks_by_quadrant(quadrant: str) -> dict:
    """Фильтрация задач по квадранту матрицы Эйзенхауэра"""
    if quadrant not in ["Q1", "Q2", "Q3", "Q4"]:
        raise HTTPException(
            status_code=400,
            detail="Неверный квадрант. Используйте: Q1, Q2, Q3, Q4"
        )
    
    filtered_tasks = [
        task for task in tasks_db
        if task["quadrant"] == quadrant
    ]
    
    return {
        "quadrant": quadrant,
        "count": len(filtered_tasks),
        "tasks": filtered_tasks
    }


@router.get("/{task_id}")
async def get_task_by_id(task_id: int) -> dict:
    """Получение задачи по ID"""
    for task in tasks_db:
        if task["id"] == task_id:
            return task
    
    raise HTTPException(
        status_code=404,
        detail=f"Задача с ID {task_id} не найдена"
    )
