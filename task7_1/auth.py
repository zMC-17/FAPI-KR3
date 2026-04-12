from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt  # type: ignore
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from models import User, UserInDB, TokenData, Permissions
from db import users_db, ROLE_PERMISSIONS

# Настройки JWT
SECRET_KEY = "your-secret-key-for-jwt-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Контекст для хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 схема
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка пароля"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Получить хеш пароля"""
    return pwd_context.hash(password)


def get_user(username: str) -> Optional[UserInDB]:
    """Получить пользователя из БД"""
    if username in users_db:
        user_data = users_db[username]
        return UserInDB(**user_data)
    return None


def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """Аутентification пользователя"""
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(
    data: dict, expires_delta: Optional[timedelta] = None
) -> str:
    """Создать JWT токен"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    """Получить текущего пользователя из токена"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    user = get_user(username=token_data.username or "")
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: UserInDB = Depends(get_current_user),
) -> UserInDB:
    """Получить активного пользователя"""
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def require_role(*roles: str):
    """Декоратор для проверки роли пользователя"""
    async def role_checker(current_user: UserInDB = Depends(get_current_active_user)):
        user_roles = set(current_user.roles)
        required_roles = set(roles)

        if not user_roles.intersection(required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions. Required roles: {', '.join(roles)}"
            )
        return current_user

    return role_checker


def require_permission(*permissions: str):
    """Декоратор для проверки разрешений пользователя"""
    async def permission_checker(current_user: UserInDB = Depends(get_current_active_user)):
        user_permissions = current_user.permissions
        required_permissions = set(permissions)

        if not required_permissions.issubset(user_permissions):
            missing = required_permissions - user_permissions
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions. Missing: {', '.join(missing)}"
            )
        return current_user

    return permission_checker


def has_permission(user: UserInDB, permission: str) -> bool:
    """Проверить наличие разрешения у пользователя"""
    return permission in user.permissions


def has_role(user: UserInDB, role: str) -> bool:
    """Проверить наличие роли у пользователя"""
    return role in user.roles
