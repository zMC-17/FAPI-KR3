from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel

app = FastAPI()

security = HTTPBasic()

DATA_BASE = [
    {"username": "user", "password": "fart"}
]

class UserModel(BaseModel):
    username: str
    password: str



def is_authentificated(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    for db_user in DATA_BASE:
        if db_user["username"] == credentials.username and db_user["password"] == credentials.password:
                return credentials.username
    raise HTTPException(status_code=401, detail="Unauthorized", headers={"WWW-Authenticate": "Basic"})


@app.post("/login")
def login(username: str = Depends(is_authentificated)):
    return {'message': "You got my secret, welcome"}
