from app.auth.services import get_user
from sqlmodel import Session, select
from app.database import get_session
from app.model import User
from app.auth.utils import get_password_hash
from fastapi import APIRouter, Depends, HTTPException, Body

router = APIRouter(prefix="/auth", tags=["Auth"])


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
        role="Usuario",
        is_Active=True,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "Usuario creado exitosamente", "user_id": new_user.id}
