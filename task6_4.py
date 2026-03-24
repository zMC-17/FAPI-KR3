from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt
import random

app = FastAPI()
security = HTTPBearer

SECRET_KEY = "Bla-bla-bla"
ALGORITHM = "H256"
EXPIRED_IN = "1m"

class UserBase(BaseModel):
    username: str

class User(UserBase):
    username: str
    password: str

'''


Проверьте токен JWT в заголовке Authorization для каждого запроса к /protected_resource. Если токен действителен,
 разрешите доступ к конечной точке и верните ответ, указывающий на успешный доступ.

Если токен недействителен, срок действия истек или отсутствует, верните соответствующий ответ об ошибке.

Примечание: Вы можете предположить существование гипотетической функции authenticate_user(username: str, password: str) -> bool,
 которая проверяет предоставленные "имя пользователя" и "пароль" по базе данных пользователя и возвращает True,
   если учетные данные действительны, и False в противном случае (или создать заглушку такой функции,
     которая при помощи модуля random.choice возвращает True или False).*
'''

def generate_jwt(payload: dict) -> str:
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def is_authorized(user: User):
    if not user.username or not user.password:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    # условная фейковая что есть такой пользователь
    if not random.choice(["True", "False"]):
        raise HTTPException(status_code=400, detail="invalid credentials")

    # Генирируем JWT
    token = generate_jwt({"sub": user.username, "password": user.password, "exp": EXPIRED_IN})
    return token

def authentication(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserBase:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload["exp"]:
            raise HTTPException (status_code=401, detail="invalid payload")
        return UserBase(username=payload["sub"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")





@app.post('/login')
def login(user: User, jwt_token = Depends(is_authorized)):
    return JSONResponse(status_code=201, content={"message": "Authorized", "token": jwt_token})

'''
Создайте защищенную конечную точку FastAPI /protected_resource, для которой требуется аутентификация с использованием JWT.
Пользователи должны включать сгенерированный токен в заголовок Authorization своих запросов для доступа к этой конечной точке.
'''

@app.get('/protected_resource')
def get_protected(user: UserBase = Depends(authentication)):
    return JSONResponse(status_code=201, content={"message": f'Hi, {user.username}, authentication is successful'})