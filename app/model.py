from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime, timezone, date

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    # Datos de login
    email: str
    username: str
    password_hash: str

    # ===== NUEVOS CAMPOS DE PERFIL =====
    nombres: Optional[str] = None          # "Ana Maria"
    apellidos: Optional[str] = None        # "González"
    telefono: Optional[str] = None         # "3001234569"
    fecha_nacimiento: Optional[date] = None
    tipo_documento: Optional[str] = None   # "CC", "TI", etc.
    numero_documento: Optional[str] = None # "1010000234"

    # ===== NUEVOS CAMPOS PARA LA PARTE DERECHA =====
    saldo: float = Field(default=0.0)
    ganancias_totales: float = Field(default=0.0)
    perdidas_totales: float = Field(default=0.0)

    role: str
    is_Active: bool
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
