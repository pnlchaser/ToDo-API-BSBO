from datetime import datetime, timezone
from typing import Optional


def calculate_urgency(deadline_at: Optional[datetime]) -> bool:
    """Определяет срочность: True если до дедлайна <= 3 дня (UTC).

    Если deadline_at is None — возвращает False.
    """
    if deadline_at is None:
        return False

    now = datetime.now(timezone.utc)
    # Если deadline_at не содержит tzinfo, считаем его в UTC
    if deadline_at.tzinfo is None:
        deadline_at = deadline_at.replace(tzinfo=timezone.utc)

    time_difference = deadline_at - now
    days_until_deadline = time_difference.days
    return days_until_deadline <= 3


def calculate_days_until_deadline(deadline_at: Optional[datetime]) -> Optional[int]:
    """Возвращает количество полных дней до дедлайна или None, если дедлайна нет."""
    if deadline_at is None:
        return None

    now = datetime.now(timezone.utc)
    if deadline_at.tzinfo is None:
        deadline_at = deadline_at.replace(tzinfo=timezone.utc)

    time_difference = deadline_at - now
    return time_difference.days


def determine_quadrant(is_important: bool, is_urgent: bool) -> str:
    """Классификация по матрице Эйзенхауэра на основе важности и срочности.
    
    Если дедлайна нет (is_urgent вычислен из None), задача попадает в Q4.
    """
    if is_important and is_urgent:
        return "Q1"
    elif is_important and not is_urgent:
        return "Q2"
    elif not is_important and is_urgent:
        return "Q3"
    else:
        return "Q4"
