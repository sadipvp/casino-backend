Casino Backend – FastAPI + SQLModel + JWT + Docker
Proyecto backend para un sistema de casino con autenticación, roles, juegos y manejo de usuarios.
Desarrollado en FastAPI, usando SQLModel, JWT

Pasos para ejecutar el proyecto 

git clone https://github.com/tuusuario/casino-backend.git 


cd casino-backend

python -m venv venv

source venv/bin/activate   # Linux

pip install -r requirements.txt

uvicorn app.main:app --reload
