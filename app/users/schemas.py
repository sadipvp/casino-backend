from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import date


class UserUpdateConctact(BaseModel):
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None


class UserUpdatePassword(BaseModel):
    old_password: str = Field(..., )
    new_password: str = Field(..., )


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
