from app.auth.utils import verify_password
from app.model import User
from sqlmodel import Session, select
from app.auth.jwt import decode_access_token


def get_user(db: Session, username: str):
    statement = select(User).where(User.username == username)
    return db.exec(statement).first()


def authenticate_user(db: Session, username: str, password: str):
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.password_hash):
        return False
    return user


def get_user_from_token(db: Session, token: str):
    payload = decode_access_token(token)
    if not payload:
        return None

    username = payload.get("sub")
    if not username:
        return None
    return get_user(db, username)
