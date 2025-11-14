from fastapi import FastAPI
from sqlmodel import SQLModel
from app.database import engine
from app import model
from contextlib import asynccontextmanager
from app.auth.routes import router as auth_router


def init_db():
    SQLModel.metadata.create_all(engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)
app.include_router(auth_router)


@app.get("/")
async def root():
    return {"message": "Hello World"}
