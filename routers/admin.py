from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Dict

from database import get_async_session
from models import User, Task
from dependencies import get_current_admin

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
)


@router.get("/users", response_model=List[Dict[str, object]])
async def list_users_with_task_counts(
    db: AsyncSession = Depends(get_async_session),
    _admin: User = Depends(get_current_admin),
):
    """Возвращает список всех пользователей с количеством их задач."""
    stmt = select(
        User.id,
        User.nickname,
        User.email,
        func.count(Task.id).label("task_count")
    ).select_from(User).join(Task, Task.user_id == User.id, isouter=True).group_by(User.id)

    result = await db.execute(stmt)
    rows = result.all()

    users = []
    for row in rows:
        # row may be RowMapping or tuple
        try:
            uid = row.id
            nickname = row.nickname
            email = row.email
            count = row.task_count
        except Exception:
            uid, nickname, email, count = row
        users.append({"id": uid, "nickname": nickname, "email": email, "task_count": count})

    return users
