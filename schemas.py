from pydantic import BaseModel, Field, computed_field
from typing import Optional
from datetime import datetime

# Базовая схема для Task
class TaskBase(BaseModel):
    title: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Название задачи"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Описание задачи"
    )
    is_important: bool = Field(
        ...,
        description="Важность задачи"
    )
    deadline_at: Optional[datetime] = Field(
        None,
        description="Плановый дедлайн задачи (опционально)"
    )

# Схема для создания новой задачи
class TaskCreate(TaskBase):
    pass

# Схема для обновления задачи
class TaskUpdate(BaseModel):
    title: Optional[str] = Field(
        None,
        min_length=3,
        max_length=100,
        description="Новое название задачи"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Новое описание"
    )
    is_important: Optional[bool] = Field(
        None,
        description="Новая важность"
    )
    deadline_at: Optional[datetime] = Field(
        None,
        description="Новый плановый дедлайн"
    )
    completed: Optional[bool] = Field(
        None,
        description="Статус выполнения"
    )

# Модель для ответа
class TaskResponse(TaskBase):
    id: int = Field(
        ...,
        description="Уникальный идентификатор задачи",
        examples= [1]
    )
    quadrant: str = Field(
        ...,
        description="Квадрант матрицы Эйзенхауэра (Q1, Q2, Q3, Q4)",
        examples=["Q1"]
    )
    completed: bool = Field(
        default=False,
        description="Статус выполнения задачи"
    )
    created_at: datetime = Field(
        ...,
        description="Дата и время создания задачи"
    )
    
    @computed_field(return_type=Optional[int])
    def days_to_deadline(self) -> Optional[int]:
        """Расчет количества полных дней от текущего UTC-времени до дедлайна."""
        if not self.deadline_at:
            return None
        # Если deadline_at — datetime без tzinfo, считаем его в UTC
        try:
            tz = self.deadline_at.tzinfo
        except Exception:
            tz = None
        now = datetime.now(tz) if tz else datetime.utcnow()
        delta = self.deadline_at.date() - now.date()
        return delta.days

    @computed_field(return_type=Optional[str])
    def status_message(self) -> Optional[str]:
        """Возвращает статус просрочена/в срок/нет дедлайна на основе days_to_deadline."""
        days = self.days_to_deadline
        if days is None:
            return None
        return "overdue" if days < 0 else "on time"
    
    class Config:
        from_attributes = True


class TimingStatsResponse(BaseModel):
    completed_on_time: int = Field(
        ...,
        description="Количество задач, завершенных в срок"
    )
    completed_late: int = Field(
        ...,
        description="Количество задач, завершенных с нарушением сроков"
    )
    on_plan_pending: int = Field(
        ...,
        description="Количество задач в работе, выполняемых в соответствии с планом"
    )
    overtime_pending: int = Field(
        ...,
        description="Количество просроченных незавершенных задач"
    )

    class Config:
        from_attributes = True
