from pydantic import BaseModel, EmailStr, Field, model_validator
from enum import Enum
from typing import Optional


class Permissions(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"


class Role(BaseModel):
    name: str
    permissions: list[str]


class User(BaseModel):
    username: str
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    disabled: bool = False
    roles: list[str]
    permissions: set[str] = Field(default_factory=set)
    extra_permissions: list[str] = Field(default_factory=list)

    @model_validator(mode='after')
    def populate_permissions(self):
        """Автоматически собираем все разрешения при создании пользователя"""
        from db import ROLE_PERMISSIONS

        all_permissions = set()
        for role_name in self.roles:
            if role_name in ROLE_PERMISSIONS:
                all_permissions.update(ROLE_PERMISSIONS[role_name])

        all_permissions.update(self.extra_permissions)
        self.permissions = all_permissions
        return self


class UserInDB(User):
    """Пользователь с хешированным паролем"""
    hashed_password: str


class UserCreate(BaseModel):
    """Схема для создания пользователя"""
    username: str
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: str
    roles: list[str] = Field(default_factory=lambda: ["guest"])


class Token(BaseModel):
    """JWT токен"""
    access_token: str
    token_type: str
    user: dict


class TokenData(BaseModel):
    """Данные из токена"""
    username: Optional[str] = None
    scopes: list[str] = Field(default_factory=list)


class Resource(BaseModel):
    """Ресурс для демонстрации RBAC"""
    id: int
    name: str
    description: str
    owner: str
    created_at: Optional[str] = None


class ResourceCreate(BaseModel):
    """Схема для создания ресурса"""
    name: str
    description: str