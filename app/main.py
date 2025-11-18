# app/main.py
from fastapi import FastAPI
from sqlmodel import SQLModel
from contextlib import asynccontextmanager

from app.database import engine
from app.auth.routes import router as auth_router
from app.profile.routes import router as profile_router  # <--- nuevo


def init_db():
    SQLModel.metadata.create_all(engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(auth_router)
app.include_router(profile_router)   # <--- nuevo


@app.get("/")
async def root():
    return {"message": "Hello World"}
