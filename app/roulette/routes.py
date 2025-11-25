# app/roulette/routes.py
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List

from sqlmodel import Session

from fastapi.security import OAuth2PasswordBearer

from app.database import get_session
from app.roulette import service as roulette_service
from app.model import RouletteSession, Spin, User
from app import config
from app.auth.services import get_user_from_token  # usamos la función existente

router = APIRouter(prefix="/v1/roulette", tags=["roulette"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# ---- request/response models ----
class CreateSessionResp(BaseModel):
    session_id: int
    server_seed_hash: str

class SpinReq(BaseModel):
    client_seed: str

class SpinResp(BaseModel):
    session_id: int
    nonce: int
    pocket: int
    color: str
    hmac_hex: str
    server_seed_hash: str

class RevealResp(BaseModel):
    session_id: int
    server_seed: str
    server_seed_hash: str
    revealed: bool

class BetReqToken(BaseModel):
    client_seed: str
    bet: dict

class BetResp(BaseModel):
    spin: dict
    bet_result: dict
    user: dict

class DepositReq(BaseModel):
    amount: float

# ---- routes ----
@router.post("/session", response_model=CreateSessionResp)
def create_session(db: Session = Depends(get_session)):
    s = roulette_service.create_session(db)
    return CreateSessionResp(session_id=s.id, server_seed_hash=s.server_seed_hash)

@router.get("/session/{session_id}/hash")
def get_session_hash(session_id: int, db: Session = Depends(get_session)):
    s = roulette_service.get_session(db, session_id)
    if not s:
        raise HTTPException(status_code=404, detail="session not found")
    return {"session_id": s.id, "server_seed_hash": s.server_seed_hash}

@router.post("/session/{session_id}/spin", response_model=SpinResp)
def spin(session_id: int, payload: SpinReq, db: Session = Depends(get_session)):
    s = roulette_service.get_session(db, session_id)
    if not s:
        raise HTTPException(status_code=404, detail="session not found")
    if s.revealed:
        raise HTTPException(status_code=400, detail="session already revealed")
    try:
        spin = roulette_service.create_spin(db, s, payload.client_seed)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return SpinResp(
        session_id=s.id,
        nonce=spin.nonce,
        pocket=spin.pocket,
        color=spin.color,
        hmac_hex=spin.hmac_hex,
        server_seed_hash=s.server_seed_hash
    )

@router.post("/session/{session_id}/bet", response_model=BetResp)
def place_bet_token(
    session_id: int,
    payload: BetReqToken,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_session)
):
    # Obtiene el usuario desde el token (usa la función que ya tienes)
    user = get_user_from_token(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    s = roulette_service.get_session(db, session_id)
    if not s:
        raise HTTPException(status_code=404, detail="session not found")
    if s.revealed:
        raise HTTPException(status_code=400, detail="session already revealed")
    try:
        result = roulette_service.create_bet(db, s, user.username, payload.bet, payload.client_seed)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result

@router.post("/session/{session_id}/reveal", response_model=RevealResp)
def reveal(session_id: int, authorization: Optional[str] = Header(None), db: Session = Depends(get_session)):
    # Authorization: Bearer <token> (admin token from .env)
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.split(" ", 1)[1]
    if token != config.ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="forbidden")

    s = roulette_service.get_session(db, session_id)
    if not s:
        raise HTTPException(status_code=404, detail="session not found")
    seed = roulette_service.reveal_session_seed(db, s)
    return RevealResp(session_id=s.id, server_seed=seed, server_seed_hash=s.server_seed_hash, revealed=True)

@router.get("/session/{session_id}/spins")
def list_spins(session_id: int, db: Session = Depends(get_session)):
    s = roulette_service.get_session(db, session_id)
    if not s:
        raise HTTPException(status_code=404, detail="session not found")
    spins = roulette_service.list_spins(db, s)
    return {"session_id": s.id, "spins": [ {
        "nonce": spin.nonce,
        "client_seed": spin.client_seed,
        "hmac_hex": spin.hmac_hex,
        "pocket": spin.pocket,
        "color": spin.color,
        "bet_type": spin.bet_type,
        "bet_amount": spin.bet_amount,
        "payout": spin.payout,
        "timestamp": spin.timestamp.isoformat()
    } for spin in spins], "revealed": s.revealed}

# ---- pequeño endpoint para depositar en el usuario (solo para pruebas) ----
@router.post("/user/deposit")
def deposit(payload: DepositReq, token: str = Depends(oauth2_scheme), db: Session = Depends(get_session)):
    user = get_user_from_token(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Cantidad inválida")
    user.saldo = (user.saldo or 0.0) + float(payload.amount)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "username": user.username, "saldo": user.saldo}
