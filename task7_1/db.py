from models import Permissions

# Определение разрешений для каждой роли
ROLE_PERMISSIONS = {
    "admin": {
        Permissions.CREATE,
        Permissions.READ,
        Permissions.UPDATE,
        Permissions.DELETE,
    },
    "user": {
        Permissions.READ,
        Permissions.UPDATE,
    },
    "guest": {
        Permissions.READ,
    },
}

# Хранилище пользователей в памяти (username -> User)
users_db: dict[str, dict] = {}