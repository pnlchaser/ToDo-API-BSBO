from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from database import AsyncSessionLocal
from models import Task
from utils import calculate_urgency, determine_quadrant
from datetime import datetime


async def update_task_urgency():
    print(f"[{datetime.now()}] Запуск автоматического обновления срочности задач...")
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(Task).where(Task.completed == False))
            tasks = result.scalars().all()
            updated_count = 0
            for task in tasks:
                new_urgency = calculate_urgency(task.deadline_at)
                new_quadrant = determine_quadrant(task.is_important, new_urgency)
                if task.is_urgent != new_urgency or task.quadrant != new_quadrant:
                    task.is_urgent = new_urgency
                    task.quadrant = new_quadrant
                    updated_count += 1
            if updated_count > 0:
                await db.commit()
                print(f"Обновлено задач: {updated_count} из {len(tasks)}")
            else:
                print(f"Изменений не требуется. Проверено задач: {len(tasks)}")
        except Exception as e:
            print(f"Ошибка при обновлении срочности: {e}")
            await db.rollback()


def start_scheduler():
    """Запускает планировщик задач и возвращает объект-планировщик."""
    scheduler = AsyncIOScheduler()
    # Ежедневно в 09:00 UTC (можно настроить в локальном времени при необходимости)
    scheduler.add_job(
        update_task_urgency,
        trigger='cron',
        hour=9,
        minute=0,
        id='update_urgency',
        name='Обновление срочности задач',
        replace_existing=True
    )

    # Для тестирования (каждые 5 минут) можно раскомментировать
    scheduler.add_job(
        update_task_urgency,
        trigger='interval',
        minutes=5,
        id='update_urgency_test',
        name='Тестовое обновление срочности',
        replace_existing=True
    )

    scheduler.start()
    print("Планировщик задач запущен")
    return scheduler
