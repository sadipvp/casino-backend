# app/games/slots/routes.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import json

from sqlmodel import Session, select
from fastapi.security import OAuth2PasswordBearer

from app.database import get_session
from app.games.slots import service as slot_service
from app.model import SlotSession, SlotSpin, User
from app.auth.services import get_user_from_token

router = APIRouter(prefix="/v1/slots", tags=["slots"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ---- Request/Response Models ----

class CreateSessionResp(BaseModel):
    session_id: int
    server_seed_hash: str


class SpinReq(BaseModel):
    client_seed: str
    bet_amount: float
    lines: Optional[int] = 1


class SpinResp(BaseModel):
    session_id: int
    nonce: int
    result: str  # "win" o "lose"
    symbols: list
    win_amount: float
    multiplier: float
    hmac_hex: str
    server_seed_hash: str


class BetReq(BaseModel):
    client_seed: str
    bet: dict  # {"amount": float, "lines": int (opcional)}


class BetResp(BaseModel):
    success: bool
    message: str
    balance: float
    spin: dict
    bet_result: dict
    user: dict


class BalanceResp(BaseModel):
    balance: float


class StatsResp(BaseModel):
    total_spins: int
    total_won: float
    total_lost: float
    biggest_win: float


class TestBetReq(BaseModel):
    client_seed: str
    bet: dict
    force_symbols: Optional[list] = None  # Para testing: ["🍒", "🍒", "🍒"]


# ---- Endpoints ----

@router.post("/session", response_model=CreateSessionResp)
def create_session(db: Session = Depends(get_session)):
    """
    1. Crear Sesión
    Crea una nueva sesión de juego
    """
    session = slot_service.create_session(db)
    return CreateSessionResp(
        session_id=session.id,
        server_seed_hash=session.server_seed_hash
    )


@router.get("/session/{session_id}/hash")
def get_session_hash(session_id: int, db: Session = Depends(get_session)):
    """
    2. Obtener Hash de Sesión
    Obtiene el hash de la sesión para verificación
    """
    session = slot_service.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session.id,
        "server_seed_hash": session.server_seed_hash
    }


@router.post("/session/{session_id}/spin", response_model=SpinResp)
def spin(
    session_id: int,
    payload: SpinReq,
    db: Session = Depends(get_session)
):
    """
    3. Girar (Spin)
    Realiza un giro del tragamonedas sin autenticación
    """
    session = slot_service.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.revealed:
        raise HTTPException(status_code=400, detail="Session already revealed")
    
    try:
        spin = slot_service.create_spin(
            db=db,
            session=session,
            client_seed=payload.client_seed,
            bet_amount=payload.bet_amount,
            lines=payload.lines or 1,
            user_id=None  # Sin usuario en este endpoint
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    symbols = json.loads(spin.symbols)
    result = "win" if spin.win_amount > 0 else "lose"
    
    return SpinResp(
        session_id=session.id,
        nonce=spin.nonce,
        result=result,
        symbols=symbols,
        win_amount=spin.win_amount,
        multiplier=spin.multiplier,
        hmac_hex=spin.hmac_hex,
        server_seed_hash=session.server_seed_hash
    )


@router.post("/session/{session_id}/bet", response_model=BetResp)
def place_bet(
    session_id: int,
    payload: BetReq,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_session)
):
    """
    4. Realizar Apuesta
    Realiza una apuesta y gira (requiere autenticación)
    """
    # Obtener usuario del token
    user = get_user_from_token(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Obtener sesión
    session = slot_service.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.revealed:
        raise HTTPException(status_code=400, detail="Session already revealed")
    
    # Extraer datos de la apuesta
    bet_amount = float(payload.bet.get("amount", 0))
    lines = int(payload.bet.get("lines", 1))
    
    # Validar saldo
    total_bet = bet_amount * lines
    if user.saldo < total_bet:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    try:
        # Realizar el spin
        spin = slot_service.create_spin(
            db=db,
            session=session,
            client_seed=payload.client_seed,
            bet_amount=bet_amount,
            lines=lines,
            user_id=user.id
        )
        
        # Actualizar saldo del usuario
        # Pasar total_bet y win_amount para actualización correcta
        user = slot_service.update_user_balance_with_bet(
            db=db,
            user_id=user.id,
            bet_amount=total_bet,
            win_amount=spin.win_amount
        )
        balance_change = spin.win_amount - total_bet
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Preparar respuesta
    symbols = json.loads(spin.symbols)
    result = "win" if spin.win_amount > 0 else "lose"
    
    return BetResp(
        success=True,
        message=f"You {'won' if result == 'win' else 'lost'}!",
        balance=user.saldo,
        spin={
            "session_id": session.id,
            "nonce": spin.nonce,
            "symbols": symbols,
            "multiplier": spin.multiplier,
            "win_amount": spin.win_amount,
            "hmac_hex": spin.hmac_hex,
            "result": result
        },
        bet_result={
            "amount": bet_amount,
            "lines": lines,
            "total_bet": total_bet,
            "win": spin.win_amount,
            "net": balance_change
        },
        user={
            "id": user.id,
            "username": user.username,
            "saldo": user.saldo,
            "ganancias_totales": user.ganancias_totales,
            "perdidas_totales": user.perdidas_totales
        }
    )


@router.get("/stats", response_model=StatsResp)
def get_stats(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_session)
):
    """
    6. Obtener Estadísticas
    Obtiene estadísticas del jugador (requiere autenticación)
    """
    user = get_user_from_token(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    stats = slot_service.get_user_stats(db, user.id)
    
    return StatsResp(**stats)


# ========== ENDPOINT DE TESTING (BORRAR EN PRODUCCIÓN) ==========
@router.post("/session/{session_id}/test-bet", response_model=BetResp)
def test_bet(
    session_id: int,
    payload: TestBetReq,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_session)
):
    """
    ENDPOINT DE TESTING - Permite forzar símbolos específicos
    Ejemplo: force_symbols: ["🍒", "🍒", "🍒"] para forzar triple cereza
    """
    user = get_user_from_token(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    session = slot_service.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    bet_amount = float(payload.bet.get("amount", 0))
    lines = int(payload.bet.get("lines", 1))
    total_bet = bet_amount * lines
    
    if user.saldo < total_bet:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    # Usar función de testing que permite forzar símbolos
    try:
        spin = slot_service.create_test_spin(
            db=db,
            session=session,
            client_seed=payload.client_seed,
            bet_amount=bet_amount,
            lines=lines,
            user_id=user.id,
            forced_symbols=payload.force_symbols  # Forzar símbolos si se proporcionan
        )
        
        user = slot_service.update_user_balance_with_bet(
            db=db,
            user_id=user.id,
            bet_amount=total_bet,
            win_amount=spin.win_amount
        )
        balance_change = spin.win_amount - total_bet
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    symbols = json.loads(spin.symbols)
    result = "win" if spin.win_amount > 0 else "lose"
    
    return BetResp(
        success=True,
        message=f"TEST MODE - You {'won' if result == 'win' else 'lost'}!",
        balance=user.saldo,
        spin={
            "session_id": session.id,
            "nonce": spin.nonce,
            "symbols": symbols,
            "multiplier": spin.multiplier,
            "win_amount": spin.win_amount,
            "hmac_hex": spin.hmac_hex,
            "result": result
        },
        bet_result={
            "amount": bet_amount,
            "lines": lines,
            "total_bet": total_bet,
            "win": spin.win_amount,
            "net": balance_change
        },
        user={
            "id": user.id,
            "username": user.username,
            "saldo": user.saldo,
            "ganancias_totales": user.ganancias_totales,
            "perdidas_totales": user.perdidas_totales
        }
    )

