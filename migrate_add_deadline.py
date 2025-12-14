"""
Скрипт миграции: добавление поля deadline_at в таблицу tasks
"""
import asyncio
from sqlalchemy import text
from database import engine

async def migrate():
    async with engine.begin() as conn:
        # Проверяем, существует ли уже колонка
        check_query = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='tasks' AND column_name='deadline_at';
        """
        result = await conn.execute(text(check_query))
        exists = result.fetchone()
        
        if exists:
            print("✓ Колонка deadline_at уже существует")
            return
        
        print("Добавляем колонку deadline_at...")
        
        # Добавляем колонку с временным значением по умолчанию
        alter_query = """
        ALTER TABLE tasks 
        ADD COLUMN deadline_at TIMESTAMP WITH TIME ZONE 
        DEFAULT (NOW() + INTERVAL '7 days') NOT NULL;
        """
        await conn.execute(text(alter_query))
        
        print("✓ Колонка deadline_at успешно добавлена")
        print("  Все существующие задачи получили дедлайн через 7 дней от текущей даты")
        print("  Вы можете обновить дедлайны вручную через API")

if __name__ == "__main__":
    asyncio.run(migrate())
    print("\n✓ Миграция завершена успешно!")
