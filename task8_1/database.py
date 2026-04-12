"""
database.py - Модуль для работы с SQLite базой данных

Этот файл содержит функции для подключения к БД и управления её жизненным циклом.
SQLite - это встроена СУБД, которая хранит БД в одном файле (users.db)
"""

import sqlite3
from typing import Optional

# Константа - имя файла БД
DATABASE_FILE = "users.db"


def get_db_connection() -> sqlite3.Connection:
    """
    Получить соединение с базой данных SQLite

    Что происходит:
    1. sqlite3.connect(DATABASE_FILE) - открывает соединение с БД
    2. Если файл не существует - создаёт его автоматически
    3. Если файл существует - подключается к нему

    Возвращает:
        sqlite3.Connection - объект соединения для выполнения SQL запросов

    Аналогия: это как если ты берёшь трубку телефона, чтобы позвонить
    """
    return sqlite3.connect(DATABASE_FILE)


def create_users_table() -> bool:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # SQL запрос для создания таблицы
        create_table_query = """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        cursor.execute(create_table_query)
        conn.commit()
        print("✓ Таблица 'users' создана/существует успешно")
        return True

    except sqlite3.Error as e:
        print(f"✗ Ошибка при создании таблицы: {e}")
        return False

    finally:
        conn.close()


def user_exists(username: str) -> bool:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Ищем пользователя
        cursor.execute("SELECT 1 FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()  # Получаем первый результат (или None если нет)

        return user is not None

    except sqlite3.Error as e:
        print(f"✗ Ошибка при проверке пользователя: {e}")
        return False

    finally:
        conn.close()


def insert_user(username: str, password: str) -> Optional[int]:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # SQL запрос для вставки
        insert_query = "INSERT INTO users (username, password) VALUES (?, ?)"

        cursor.execute(insert_query, (username, password))
        conn.commit()

        # Получаем ID последней вставленной записи
        user_id = cursor.lastrowid

        print(f"✓ Пользователь '{username}' добавлен с ID {user_id}")
        return user_id

    except sqlite3.IntegrityError as e:
        print(f"✗ Ошибка: username '{username}' уже существует!")
        return None

    except sqlite3.Error as e:
        print(f"✗ Ошибка при добавлении пользователя: {e}")
        return None

    finally:
        conn.close()