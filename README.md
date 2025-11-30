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



Endpoints principales

Auth -------

POST /auth/signup → Crear usuario

POST /auth/login → Login y generación de JWT

GET /auth/me → Consultar usuario desde token

GET /Debug/users → Listar todos los usuarios

User --------

PATCH /profile/me/update -> modificar telefono y email

PATCH /profile/me/password -> modificar contraseña vieja

GET   /profile/me/saldo -> Devuelve el saldo del usuario a partir del Token

GET   /profile/{username} -> Devuelve la informacion del usuario   



Variables de entorno

Crear archivo .env en la raíz:

SECRET_KEY=tu_clave_secreta

DATABASE_URL=sqlite:///./casino.db

