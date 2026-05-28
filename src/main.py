from fastapi import FastAPI
from .schemas import UserCreate

app = FastAPI()

@app.post("/registration")
async def registration(user: UserCreate):
    return {"msg": "User created", "user": user.username}