## 🚀 Быстрый старт

### 1. Запуск приложения

```bash
cd task8_1
python main.py
# Приложение на http://localhost:8000
```

### 2. Регистрация пользователя (curl)

```bash
curl -X POST "http://localhost:8000/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "john_doe", "password": "12345678"}'

# Ответ:
# {"id": 1, "username": "john_doe", "message": "User 'john_doe' успешно зарегистрирован!"}
```
