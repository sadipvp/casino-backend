# app/main.py
from fastapi import FastAPI
from sqlmodel import SQLModel
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine
from app.auth.routes import router as auth_router

from app.games.slot_machine.routes import router as slot_router
from app.games.roulette.routes import router as roulette_router  # <- nueva línea

from app.users.routes import router as profile_router  # <--- nuevo


def init_db():
    SQLModel.metadata.create_all(engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Frontend DEV
        "http://127.0.0.1:5173",
        "*",  # (solo para desarrollo)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(profile_router)   # <--- nuevo
app.include_router(slot_router)
app.include_router(roulette_router)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/ping")
async def ping():
    return {"pong"}
