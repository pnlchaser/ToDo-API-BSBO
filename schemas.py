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
    deadline_at: datetime = Field(
        ...,
        description="Плановый дедлайн задачи"
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
    
    @computed_field(return_type=int)
    def days_to_deadline(self) -> int:
        """Расчет количества дней от сегодняшней даты до дедлайна."""
        now = datetime.now(self.deadline_at.tzinfo) if self.deadline_at.tzinfo else datetime.now()
        delta = self.deadline_at.date() - now.date()
        return delta.days
    
    class Config:
        from_attributes = True
