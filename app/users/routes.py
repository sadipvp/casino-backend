# app/profile/routes.py
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session
from fastapi.security import OAuth2AuthorizationCodeBearer
from app.users.dependencies import get_current_user
from app.database import get_session
from app.users.services import get_profile_by_username, update_user_contact
from app.model import User
from app.users.schemas import UserUpdateConctact, PerfilResponse, UserUpdatePassword
from app.auth.utils import verify_password, get_password_hash


router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("/{username}", response_model=PerfilResponse)
def get_profile(username: str, db: Session = Depends(get_session)):
    """
    NO usa JWT. El front envía el username en la URL:
    GET /profile/anago2025
    """
    user: User | None = get_profile_by_username(db, username)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return PerfilResponse(
        nombres=user.name,
        apellidos=user.apellidos,
        usuario=user.username,
        correo_electronico=user.email,
        telefono=user.telefono,
        fecha_nacimiento=user.fecha_nacimiento,
        tipo_documento=user.tipo_documento,
        numero_documento=user.numero_documento,
        saldo=user.saldo,
        ganancias_totales=user.ganancias_totales,
        perdidas_totales=user.perdidas_totales,
    )


@router.patch("/me/update", response_model=UserUpdateConctact)
def update_user(
    contact_in: UserUpdateConctact,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):

    if contact_in.email is not None:
        current_user.email = contact_in.email
    if contact_in.telefono is not None:
        current_user.telefono = contact_in.telefono

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return UserUpdateConctact(
        email=current_user.email,
        telefono=current_user.telefono,
    )


@router.patch("/me/password")
def update_Password(
        contact_in: UserUpdatePassword,
        db: Session = Depends(get_session),
        current_user: User = Depends(get_current_user),
):
    if verify_password(contact_in.old_password, current_user.password_hash):
        if contact_in.old_password != contact_in.new_password:
            new_password = get_password_hash(contact_in.new_password)
            current_user.password_hash = new_password

            db.add(current_user)
            db.commit()
            db.refresh(current_user)

    else:
        return {"message": "La contraseña no coincide con la anterior "}
    return {"message": "La contraseña ha sido actualizada"}


@router.get("/me/saldo")
def User_saldo(
    current_user: User = Depends(get_current_user),
):
    return { "saldo": current_user.saldo }

#### solo development ####
@router.get("/id/{user_id}")
def get_username_by_id(
    user_id: int,
    db: Session = Depends(get_session),
):
    """
    Obtiene el username de un usuario a partir de su ID.
    Ejemplo: GET /profile/id/1
    """
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    return {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "name": user.name,
        "role": user.role
    }


@router.get("/add-balance/{user_id}/{amount}")
def add_balance_to_user(
    user_id: int,
    amount: float,
    db: Session = Depends(get_session),
):
    """
    Agrega saldo a un usuario específico mediante URL.
    Ejemplo: GET /profile/add-balance/1/100.50
    """
    if amount <= 0:
        raise HTTPException(status_code=400, detail="El monto debe ser mayor a 0")
    
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    user.saldo += amount
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {
        "message": "Saldo agregado exitosamente",
        "user_id": user.id,
        "username": user.username,
        "saldo_anterior": user.saldo - amount,
        "monto_agregado": amount,
        "saldo_nuevo": user.saldo
    }
