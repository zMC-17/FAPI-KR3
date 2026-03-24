from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from passlib.context import CryptContext
import secrets


app = FastAPI()
security = HTTPBasic()
passlib_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = "BLA-BLA-BLA"

# Модели данных
class UserBase(BaseModel):
    username: str

class User(UserBase):
     password: str

class UserInDB(UserBase):
     hashed_password: str

fake_users_db = [
    UserInDB(username="Vasya", hashed_password=passlib_context.hash("secret123"))
]

def auth_user(credentials: HTTPBasicCredentials = Depends(security)) -> UserBase:
    input_username = credentials.username
    input_password = credentials.password

    for user in fake_users_db:
        if secrets.compare_digest(user.username, input_username):
            #Проверяем пароль с помощью контекста
            pass_is_correct = passlib_context.verify(input_password, user.hashed_password)
            if not pass_is_correct:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid credentials",
                    headers={"WWW-Authenticate": "Basic"}
                )
            # ЧТО ТАКОЕ secrets.compare_digest() и зачем мне это здесь применять?
            return UserBase(username = input_username)
    raise HTTPException(status_code=401, detail="invalid credentials", headers={"WWW-Authenticate": "Basic"})

@app.post('/register')
def register(user: User):

    try:
        password = passlib_context.hash(user.password)
        new_user_record = UserInDB(username = user.username, hashed_password=password)
        fake_users_db.append(new_user_record)
        return JSONResponse(status_code=201, content={"message": "Registration is successful. User has been added"})
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Registration failed: str{e}")

@app.get("/login")
def login(user: UserBase = Depends(auth_user)):
    return {'message': f'Welcome, {user.username}!'}
