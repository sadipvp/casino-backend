from fastapi import FastAPI
from app import routes

app = FastAPI(title="Casino Backend", version="1.0.0")

app.include_router(routes.router)


@app.get("/")
def root():
    return {"message": "Bienvenido al Casino API 🎰"}
