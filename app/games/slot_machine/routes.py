from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List
import random

# Si quieres proteger el juego con login:
# from sqlmodel import Session
# from app.database import get_session
# from app.auth.jwt import decode_access_token
# from fastapi.security import OAuth2PasswordBearer

router = APIRouter(prefix="/games", tags=["Games"])

# =======================
#   TRAGAMONEDAS
# =======================

SYMBOLS = ["CHERRY", "LEMON", "BAR", "SEVEN", "DIAMOND"]


class SlotBetRequest(BaseModel):
    amount: float = Field(gt=0, description="Monto apostado, debe ser > 0")


class SlotSpinResult(BaseModel):
    reels: List[str]
    bet: float
    win_amount: float
    is_win: bool
    rule: str


def spin_reels() -> list[str]:
    """Devuelve una lista de 3 símbolos aleatorios."""
    return [random.choice(SYMBOLS) for _ in range(3)]


def calculate_payout(reels: list[str], bet: float) -> tuple[float, str]:
    """
    Devuelve (monto_ganado, regla_aplicada).
    """
    # Contar repetidos
    a, b, c = reels
    unique = set(reels)

    # 3 iguales
    if len(unique) == 1:
        return bet * 5, "3 iguales → pago x5"

    # 2 iguales
    if len(unique) == 2:
        return bet * 2, "2 iguales → pago x2"

    # Ningún premio
    return 0.0, "Sin combinación ganadora"


@router.post("/slots/spin", response_model=SlotSpinResult)
def play_slots(payload: SlotBetRequest):
    # 1. Obtener apuesta
    bet = payload.amount

    # 2. Generar resultado del tragamonedas
    reels = spin_reels()

    # 3. Calcular premio
    win_amount, rule = calculate_payout(reels, bet)

    # 4. Aquí podrías actualizar saldo del usuario en la DB
    #    - Restar bet
    #    - Sumar win_amount
    #    Pero eso lo hacemos cuando conectes esto con tu modelo User.

    return SlotSpinResult(
        reels=reels,
        bet=bet,
        win_amount=win_amount,
        is_win=win_amount > 0,
        rule=rule,
    )
