"""
Миграция: делаем столбец deadline_at опциональным (nullable=True)
"""
import asyncio
from sqlalchemy import text
from database import engine

async def migrate():
    async with engine.begin() as conn:
        print("Обновляем столбец deadline_at на nullable=TRUE...")
        
        # PostgreSQL синтаксис для изменения nullable
        alter_query = """
        ALTER TABLE tasks 
        ALTER COLUMN deadline_at DROP NOT NULL;
        """
        try:
            await conn.execute(text(alter_query))
            print("✓ Столбец deadline_at успешно обновлен (теперь nullable)")
        except Exception as e:
            print(f"Ошибка при обновлении: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(migrate())
    print("\n✓ Миграция завершена успешно!")
