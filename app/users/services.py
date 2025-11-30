# app/profile/services.py
from sqlmodel import Session, select
from app.model import User
from app.users.schemas import UserUpdateConctact
from fastapi import HTTPException, Depends
from app.auth.services import get_user_from_token
from app.database import get_session


def get_profile_by_username(db: Session, username: str) -> User | None:
    """
    Devuelve el usuario (con todos los datos de perfil) por username.
    """
    stmt = select(User).where(User.username == username)
    return db.exec(stmt).first()


def update_user_contact(
        username: str,
        contact_in: UserUpdateConctact,
        db: Session = Depends(get_session),
        token: str = Depends()) -> User | None:

    user = db.get(User, username)

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    data = contact_in.model_dump(exclude_unset=True)

    if not data:
        raise HTTPException(
            status_code=400, detail="No hay datos para actualizar")

    for field, value in data.items():
        setattr(user, field, value)

    db.add(user)
    db.commit()
    db.refresh(user)
    return user
