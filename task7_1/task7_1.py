from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from datetime import timedelta, datetime
from typing import Optional
from models import (
    User, UserInDB, UserCreate, Token, Resource, ResourceCreate, Permissions
)
from db import users_db, ROLE_PERMISSIONS
from auth import (
    authenticate_user, create_access_token, get_current_active_user,
    get_password_hash, require_role, require_permission, has_permission,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

app = FastAPI(title="RBAC FastAPI", version="1.0.0")

# Хранилище ресурсов в памяти
resources_db = {}
resource_id_counter = 1


# ============= ЭНДПОИНТЫ АУТЕНТИФИКАЦИИ =============

@app.post("/register", response_model=User)
async def register(user_data: UserCreate):
    """Регистрация нового пользователя"""
    if user_data.username in users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    hashed_password = get_password_hash(user_data.password)

    new_user = UserInDB(
        username=user_data.username,
        full_name=user_data.full_name,
        email=user_data.email,
        hashed_password=hashed_password,
        roles=user_data.roles or ["guest"],
        disabled=False
    )

    # Сохраняем в БД
    users_db[user_data.username] = new_user.model_dump()

    return User(**new_user.model_dump())


@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Получить JWT токен (логин)"""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "scopes": list(user.roles)},
        expires_delta=access_token_expires
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        user={
            "username": user.username,
            "roles": user.roles,
            "permissions": list(user.permissions)
        }
    )


@app.get("/me", response_model=User)
async def read_users_me(current_user: UserInDB = Depends(get_current_active_user)):
    """Получить информацию о текущем пользователе"""
    return User(**current_user.model_dump())


# ============= ЗАЩИЩЁННЫЕ РЕСУРСЫ =============

@app.get("/protected_resource")
async def protected_resource(current_user: UserInDB = Depends(get_current_active_user)):
    """Защищённый ресурс - доступ только для аутентифицированных пользователей"""
    return {
        "message": f"Hello {current_user.username}!",
        "user_roles": current_user.roles,
        "user_permissions": list(current_user.permissions)
    }


# ============= РЕСУРСЫ (CRUD) =============

@app.post("/resources", response_model=Resource, status_code=status.HTTP_201_CREATED)
async def create_resource(
    resource: ResourceCreate,
    current_user: UserInDB = Depends(require_permission(Permissions.CREATE))
):
    """Создать ресурс - требуется разрешение CREATE (admin или user с дополнительными правами)"""
    global resource_id_counter

    resource_id = resource_id_counter
    resource_id_counter += 1

    new_resource = Resource(
        id=resource_id,
        name=resource.name,
        description=resource.description,
        owner=current_user.username,
        created_at=str(datetime.now())
    )

    resources_db[resource_id] = new_resource.model_dump()
    return new_resource


@app.get("/resources", response_model=list[Resource])
async def list_resources(
    current_user: UserInDB = Depends(require_permission(Permissions.READ))
):
    """Получить список всех ресурсов - требуется разрешение READ"""
    return [Resource(**res) for res in resources_db.values()]


@app.get("/resources/{resource_id}", response_model=Resource)
async def get_resource(
    resource_id: int,
    current_user: UserInDB = Depends(require_permission(Permissions.READ))
):
    """Получить ресурс по ID - требуется разрешение READ"""
    if resource_id not in resources_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )
    return Resource(**resources_db[resource_id])


@app.put("/resources/{resource_id}", response_model=Resource)
async def update_resource(
    resource_id: int,
    resource: ResourceCreate,
    current_user: UserInDB = Depends(require_permission(Permissions.UPDATE))
):
    """Обновить ресурс - требуется разрешение UPDATE"""
    if resource_id not in resources_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )

    existing_resource = resources_db[resource_id]

    # Проверяем, что пользователь - владелец или admin
    if existing_resource["owner"] != current_user.username and "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only update your own resources"
        )

    updated_resource = Resource(
        id=resource_id,
        name=resource.name,
        description=resource.description,
        owner=existing_resource["owner"],
        created_at=existing_resource["created_at"]
    )

    resources_db[resource_id] = updated_resource.model_dump()
    return updated_resource


@app.delete("/resources/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(
    resource_id: int,
    current_user: UserInDB = Depends(require_permission(Permissions.DELETE))
):
    """Удалить ресурс - требуется разрешение DELETE (только admin)"""
    if resource_id not in resources_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )

    del resources_db[resource_id]
    return None


# ============= ЭНДПОИНТЫ ДЛЯ АДМИНИСТРАТОРОВ =============

@app.get("/admin/stats")
async def admin_stats(
    current_user: UserInDB = Depends(require_role("admin"))
):
    """Получить статистику - только для администраторов"""
    return {
        "total_users": len(users_db),
        "total_resources": len(resources_db),
        "roles_info": {
            "admin": f"{sum(1 for u in users_db.values() if 'admin' in u['roles'])} users",
            "user": f"{sum(1 for u in users_db.values() if 'user' in u['roles'])} users",
            "guest": f"{sum(1 for u in users_db.values() if 'guest' in u['roles'])} users"
        }
    }


@app.get("/admin/users", response_model=list[User])
async def list_all_users(
    current_user: UserInDB = Depends(require_role("admin"))
):
    """Получить список всех пользователей - только для администраторов"""
    return [User(**user) for user in users_db.values()]


@app.put("/admin/users/{username}/roles")
async def update_user_roles(
    username: str,
    roles: list[str],
    current_user: UserInDB = Depends(require_role("admin"))
):
    """Обновить роли пользователя - только для администраторов"""
    if username not in users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    valid_roles = {"admin", "user", "guest"}
    if not set(roles).issubset(valid_roles):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid roles. Must be one of: {', '.join(valid_roles)}"
        )

    user_data = users_db[username]
    user_data["roles"] = roles

    # Пересчитываем разрешения
    user_obj = UserInDB(**user_data)
    users_db[username] = user_obj.model_dump()

    return {
        "message": f"Roles updated for {username}",
        "new_roles": roles,
        "permissions": list(user_obj.permissions)
    }


# ============= ЭНДПОИНТЫ ДЛЯ ОБЫЧНЫХ ПОЛЬЗОВАТЕЛЕЙ =============

@app.get("/user/profile", response_model=User)
async def user_profile(
    current_user: UserInDB = Depends(require_role("user", "admin"))
):
    """Получить свой профиль - для user и admin"""
    return User(**current_user.model_dump())


@app.get("/user/resources", response_model=list[Resource])
async def user_resources(
    current_user: UserInDB = Depends(require_role("user", "admin"))
):
    """Получить ресурсы текущего пользователя"""
    user_resources = [
        Resource(**res) for res in resources_db.values()
        if res["owner"] == current_user.username
    ]
    return user_resources


# ============= ЭНДПОИНТЫ ДЛЯ ГОСТЕЙ =============

@app.get("/guest/info")
async def guest_info(
    current_user: UserInDB = Depends(require_role("guest", "user", "admin"))
):
    """Получить информацию (только чтение) - для всех"""
    return {
        "message": f"Welcome {current_user.username}!",
        "your_roles": current_user.roles,
        "available_permissions": list(current_user.permissions)
    }


# ============= ИНФОРМАЦИОННЫЕ ЭНДПОИНТЫ =============

@app.get("/info/roles")
async def get_roles_info():
    """Получить информацию о ролях и разрешениях"""
    return {
        "admin": {
            "description": "Full access to all resources",
            "permissions": list(ROLE_PERMISSIONS["admin"])
        },
        "user": {
            "description": "Can read and update resources",
            "permissions": list(ROLE_PERMISSIONS["user"])
        },
        "guest": {
            "description": "Read-only access",
            "permissions": list(ROLE_PERMISSIONS["guest"])
        }
    }


@app.get("/")
async def root():
    """Root endpoint с информацией о приложении"""
    return {
        "title": "RBAC FastAPI Application",
        "version": "1.0.0",
        "description": "Role-Based Access Control system",
        "endpoints": {
            "authentication": [
                "POST /register - Register new user",
                "POST /token - Get JWT token (login)",
                "GET /me - Get current user info"
            ],
            "protected": [
                "GET /protected_resource - Protected resource"
            ],
            "resources": [
                "POST /resources - Create resource",
                "GET /resources - List all resources",
                "GET /resources/{id} - Get resource",
                "PUT /resources/{id} - Update resource",
                "DELETE /resources/{id} - Delete resource"
            ],
            "admin": [
                "GET /admin/stats - Get statistics",
                "GET /admin/users - List all users",
                "PUT /admin/users/{username}/roles - Update user roles"
            ],
            "user": [
                "GET /user/profile - Get profile",
                "GET /user/resources - Get own resources"
            ],
            "info": [
                "GET /info/roles - Get roles info",
                "GET /guest/info - Get guest info"
            ]
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
