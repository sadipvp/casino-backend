from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime, timezone, date
from sqlalchemy import UniqueConstraint


class User(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("username"),)
    id: Optional[int] = Field(default=None, primary_key=True)

    # Datos de login
    email: str
    username: str
    password_hash: str

   

    name: Optional[str] = None
    apellidos: Optional[str] = None        
    telefono: Optional[str] = None        
    fecha_nacimiento: Optional[date] = None
    tipo_documento: Optional[str] = None   
    numero_documento: Optional[str] = None 

    # ===== NUEVOS CAMPOS PARA LA PARTE DERECHA =====
    saldo: float = Field(default=500.0)
    ganancias_totales: float = Field(default=0.0)
    perdidas_totales: float = Field(default=0.0)

    role: str
    is_Active: bool
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class RouletteSession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # server_seed (hex) guardado cifrado/en DB; en producción deberías cifrarlo o usar KMS
    server_seed: str
    server_seed_hash: str
    nonce: int = Field(default=0)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))
    revealed: bool = Field(default=False)

    # relación inversa (no obligatorio)
    spins: List["Spin"] = Relationship(back_populates="session")


class Spin(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="roulettesession.id")
    nonce: int
    client_seed: str
    hmac_hex: str
    pocket: int
    color: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))

    # ---- nuevos campos para apuestas ----
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    # e.g. "straight", "color", "odd_even"...
    bet_type: Optional[str] = None
    # texto JSON con los detalles (ej. '{"number":17}')
    bet_payload: Optional[str] = None
    bet_amount: float = Field(default=0.0)
    payout: float = Field(default=0.0)           # ganancia neta o -stake

    session: Optional[RouletteSession] = Relationship(back_populates="spins")

class CreditRequest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    amount: float
    status: str = Field(default="pending")  # pending / approved / denied
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed_at: Optional[datetime] = None
    reviewer_id: Optional[int] = Field(default=None, foreign_key="user.id")
    note: Optional[str] = None

    # relación opcional para uso en consultas
    # user: Optional[User] = Relationship(back_populates="credit_requests")


class SlotSession(SQLModel, table=True):
    """Sesión de slot machine con sistema provably fair"""
    id: Optional[int] = Field(default=None, primary_key=True)
    server_seed: str  # Seed del servidor (se mantiene secreto hasta reveal)
    server_seed_hash: str  # Hash público del server seed
    nonce: int = Field(default=0)  # Contador de spins
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    revealed: bool = Field(default=False)  # Si el seed fue revelado
    
    # Relación con spins
    spins: List["SlotSpin"] = Relationship(back_populates="session")


class SlotSpin(SQLModel, table=True):
    """Registro de cada giro de slot machine"""
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="slotsession.id")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    
    # Provably fair
    nonce: int
    client_seed: str
    hmac_hex: str
    
    # Resultado del giro
    symbols: str  # JSON con los símbolos resultantes, ej: '["🍒","🍋","🍊"]'
    multiplier: float = Field(default=0.0)  # Multiplicador ganado
    
    # Apuesta y ganancia
    bet_amount: float = Field(default=0.0)
    lines: int = Field(default=1)  # Número de líneas apostadas
    win_amount: float = Field(default=0.0)  # Cantidad ganada
    
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Relación inversa
    session: Optional[SlotSession] = Relationship(back_populates="spins")
