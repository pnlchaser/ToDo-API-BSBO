from fastapi import FastAPI
from routers import tasks, stats

app = FastAPI(
    title="ToDo лист API",
    description="API для управления задачами с матрицей Эйзенхауэра",
    version="1.0.0",
    contact={"name": "Чистяков Сергей"}
)

# Подключаем роутеры с префиксом /api/v1
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(stats.router, prefix="/api/v1")


@app.get("/")
async def root() -> dict:
    """Корневой маршрут с информацией об API"""
    return {
        "message": "Привет студент!",
        "api_title": app.title,
        "api_version": app.version,
        "api_description": app.description,
        "api_author": app.contact["name"]
    }
