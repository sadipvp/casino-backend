from fastapi import Depends, HTTPException
from app.database import get_session
from fastapi.security import OAuth2PasswordBearer
from app.model import User
from sqlmodel import Session
from app.auth.services import get_user_from_token


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    db: Session = Depends(get_session),
    token: str = Depends(oauth2_scheme),
) -> User | None:

    user = get_user_from_token(db, token)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Token invalido o usuario no encontrado"
        )
    return user
