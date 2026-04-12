"""
main.py - Основное FastAPI приложение с эндпоинтом регистрации

Это приложение предоставляет API для регистрации пользователей с сохранением в SQLite БД.
"""

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from database import create_users_table, insert_user, user_exists

# Инициализация FastAPI приложения
app = FastAPI()


# ============================================================================
# PYDANTIC МОДЕЛИ - Валидация данных
# ============================================================================

class UserRegister(BaseModel):
    """
    Модель для регистрации пользователя

    Что это:
    - Pydantic автоматически валидирует входящие данные
    - Проверяет типы (username и password должны быть string)
    - Проверяет что они не пусты
    - Генерирует JSON схему для документации
    """
    username: str = Field(..., min_length=3, max_length=50, description="Имя пользователя (3-50 символов)")
    password: str = Field(..., min_length=6, max_length=100, description="Пароль (минимум 6 символов)")


class UserResponse(BaseModel):
    """Модель ответа при успешной регистрации"""
    id: int
    username: str
    message: str


class ErrorResponse(BaseModel):
    """Модель для ошибок"""
    detail: str


# ============================================================================
# ЗАПУСК - Инициализация при старте приложения
# ============================================================================

@app.on_event("startup")
async def startup_event():
    print("\n" + "="*60)
    print("🚀 Запуск приложения User Registration API")
    print("="*60)

    if create_users_table():
        print("✓ БД инициализирована успешно\n")
    else:
        print("✗ Ошибка инициализации БД\n")


# ============================================================================
# ЭНДПОИНТЫ
# ============================================================================

@app.get("/", tags=["Info"])
async def root():
    """Корневой эндпоинт с информацией о API"""
    return {
        "title": "User Registration API",
        "version": "1.0.0",
        "endpoints": {
            "register": "POST /register - Регистрация нового пользователя",
            "health": "GET /health - Проверка здоровья приложения",
            "users_debug": "GET /users_debug - Список всех пользователей (отладка)"
        }
    }

@app.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Auth"],
    summary="Регистрация нового пользователя",
    responses={
        201: {"description": "Пользователь успешно зарегистрирован"},
        400: {"description": "Ошибка - username уже существует или некорректные данные"},
        422: {"description": "Ошибка валидации данных"}
    }
)
async def register(user: UserRegister):

    # ШАГ 1: Проверка что username уникален
    if user_exists(user.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{user.username}' уже зарегистрирован!"
        )

    # ШАГ 2: Вставляем пользователя в БД
    user_id = insert_user(user.username, user.password)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка при регистрации!" # Реальная ошибка залогирована в БД
        )

    # ШАГ 3: Возвращаем успешный ответ
    return UserResponse(
        id=user_id,
        username=user.username,
        message=f"User '{user.username}' успешно зарегистрирован!"
    )

# ============================================================================
# ЗАПУСК ПРИЛОЖЕНИЯ
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
