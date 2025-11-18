# app/profile/routes.py
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.database import get_session
from app.profile.services import get_profile_by_username
from app.model import User

router = APIRouter(prefix="/profile", tags=["Profile"])


class PerfilResponse(BaseModel):
    # Columna izquierda
    nombres: Optional[str]
    apellidos: Optional[str]
    usuario: str
    correo_electronico: str
    telefono: Optional[str]
    fecha_nacimiento: Optional[date]
    tipo_documento: Optional[str]
    numero_documento: Optional[str]

    # Columna derecha
    saldo: float
    ganancias_totales: float
    perdidas_totales: float


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
        nombres=user.nombres,
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
