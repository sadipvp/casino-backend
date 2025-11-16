from app.auth.services import get_user, authenticate_user
from sqlmodel import Session, select
from app.database import get_session
from app.model import User
from app.auth.utils import get_password_hash
from fastapi import APIRouter, Depends, HTTPException, Body
from app.auth.jwt import decode_access_token, create_access_token
from fastapi.security import OAuth2PasswordBearer


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
        "role": user.role

    }


@router.post("/signup")
def signup(
    payload: dict = Body(...),
    db: Session = Depends(get_session)
):

    email = payload.get("email")
    username = payload.get("username")
    password = payload.get("password")

    user_exists = get_user(db, username)
    if user_exists:
        raise HTTPException(status_code=400, detail="El usuario ya existe")

    hashed = get_password_hash(password)

    new_user = User(
        email=email,
        username=username,
        password_hash=hashed,
        role="Jugador",
        is_Active=True,
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


def get_user_from_token(db: Session, token: str):
    payload = decode_access_token(token)
    if not payload:
        return None

    username = payload.get("sub")
    if not username:
        return None

    return get_user(db, username)
