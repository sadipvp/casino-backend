from app.auth.services import get_user, authenticate_user
from sqlmodel import Session, select
from app.database import get_session
from app.model import User
from app.auth.utils import get_password_hash
from fastapi import APIRouter, Depends, HTTPException, Body
from app.auth.jwt import decode_access_token, create_access_token
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime

router = APIRouter(prefix="/auth", tags=["Auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@router.get("/me")
def me(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_session)
):
    user = get_user_from_token(db, token)
    if not user:
        raise HTTPException(
            status_code=401, detail="Token Invalido o expirado")

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "nombres": user.name,
        "apellidos": user.apellidos,
        "telefonos": user.telefono,
        "fecha_nacimiento": user.fecha_nacimiento,
        "cedula": user.numero_documento

    }


@router.post("/signup")
def signup(
    payload: dict = Body(...),
    db: Session = Depends(get_session)
):

    email = payload.get("email")
    username = payload.get("username")
    password = payload.get("password")
    name = payload.get("name")
    last_name = payload.get("apellidos")
    cellphone_number = payload.get("telefono")
    born_date = payload.get("born_date")
    id = payload.get("cedula")
    type_id = payload.get("tipo_documento")

    user_exists = get_user(db, username)
    if user_exists:
        raise HTTPException(status_code=400, detail="El usuario ya existe")

    if isinstance(payload.get("born_date"), str):
        born_date = datetime.strptime(
            payload.get("born_date"), "%Y-%m-%d"
        ).date()

    hashed = get_password_hash(password)

    new_user = User(
        email=email,
        username=username,
        password_hash=hashed,
        role="Jugador",
        is_Active=True,
        name=name,
        apellidos=last_name,
        telefono=cellphone_number,
        fecha_nacimiento=born_date,
        tipo_documento=type_id,
        numero_documento=id
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "Usuario creado exitosamente", "user_id": new_user.id}


@router.post("/login")
def login(
    datas: dict = Body(...),
    db: Session = Depends(get_session)
):

    username = datas.get("username")
    password = datas.get("password")

    user_exists = get_user(db, username)
    if not username or not password:
        raise HTTPException(status_code=400, detail="Faltan datos")

    user = authenticate_user(db, username, password)

    if not user:
        raise HTTPException(
            status_code=404, details="Credenciales incorrectas")

    token = create_access_token({"sub": user.username})

    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user.username,
        "role": user.role
    }


@router.get("/debug/users")
def Debug_Users(db: Session = Depends(get_session)):
    statement = select(User)
    users = db.exec(statement).all()
    return users


@router.get("/create-admin")
def create_admin_user(db: Session = Depends(get_session)):
    """
    Crea un usuario admin de prueba. Solo accede a la URL.
    GET /auth/create-admin
    """
    username = "admin"
    password = "admin"
    email = "admin@test.com"
    
    # Verificar si el usuario ya existe
    user_exists = get_user(db, username)
    if user_exists:
        raise HTTPException(status_code=400, detail="El usuario admin ya existe")
    
    hashed = get_password_hash(password)
    
    new_admin = User(
        email=email,
        username=username,
        password_hash=hashed,
        role="admin",
        is_Active=True,
        name="Admin",
        apellidos="Test",
        saldo=10000.0
    )
    
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    
    return {
        "message": "Usuario administrador creado exitosamente",
        "username": "admin",
        "password": "admin",
        "role": "admin",
        "saldo": 10000.0
    }


def get_user_from_token(db: Session, token: str):
    payload = decode_access_token(token)
    if not payload:
        return None

    username = payload.get("sub")
    if not username:
        return None

    return get_user(db, username)
