# app/profile/services.py
from sqlmodel import Session, select
from app.model import User


def get_profile_by_username(db: Session, username: str) -> User | None:
    """
    Devuelve el usuario (con todos los datos de perfil) por username.
    """
    stmt = select(User).where(User.username == username)
    return db.exec(stmt).first()
