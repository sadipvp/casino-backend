# app/games/slots/service.py
import secrets
import hashlib
import hmac
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from sqlmodel import Session, select, func
from app.model import SlotSession, SlotSpin, User

# --- Símbolos y multiplicadores ---
SLOT_SYMBOLS = ["🍒", "🍋", "🍊", "🍇", "💎", "⭐", "7️⃣"]

# Probabilidades y pagos
SYMBOL_PAYOUTS = {
    "7️⃣": 50.0,    # Triple 7 - jackpot
    "💎": 25.0,     # Triple diamante
    "⭐": 15.0,     # Triple estrella
    "🍇": 10.0,     # Triple uvas
    "🍊": 8.0,      # Triple naranja
    "🍋": 5.0,      # Triple limón
    "🍒": 3.0,      # Triple cereza
}

# ---- Provably fair helpers ----
def generate_server_seed() -> str:
    """Genera un seed aleatorio del servidor"""
    return secrets.token_hex(32)


def hash_server_seed(server_seed: str) -> str:
    """Genera el hash SHA-256 del server seed"""
    return hashlib.sha256(server_seed.encode()).hexdigest()


def hmac_sha256_hex(key_hex: str, message: str) -> str:
    """Genera HMAC-SHA256 en hexadecimal"""
    key = bytes.fromhex(key_hex)
    hm = hmac.new(key, message.encode(), hashlib.sha256)
    return hm.hexdigest()


def derive_symbols_from_hmac(hmac_hex: str, num_reels: int = 3) -> List[str]:
    """
    Deriva símbolos de forma determinística desde el HMAC.
    Usa diferentes partes del hash para cada carrete.
    """
    symbols = []
    hash_int = int(hmac_hex, 16)
    
    for i in range(num_reels):
        # Usa diferentes segmentos del hash para cada carrete
        segment = (hash_int >> (i * 8)) % len(SLOT_SYMBOLS)
        symbols.append(SLOT_SYMBOLS[segment])
    
    return symbols


def calculate_multiplier(symbols: List[str]) -> float:
    """
    Calcula el multiplicador basado en los símbolos obtenidos.
    Si los 3 símbolos coinciden, aplica el pago de SYMBOL_PAYOUTS.
    """
    if len(symbols) != 3:
        return 0.0
    
    # Verificar si todos los símbolos son iguales
    if symbols[0] == symbols[1] == symbols[2]:
        return SYMBOL_PAYOUTS.get(symbols[0], 0.0)
    
    # No hay coincidencia
    return 0.0


# ---- DB operations ----
def create_session(db: Session) -> SlotSession:
    """Crea una nueva sesión de slot machine"""
    server_seed = generate_server_seed()
    session = SlotSession(
        server_seed=server_seed,
        server_seed_hash=hash_server_seed(server_seed),
        nonce=0,
        revealed=False
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: Session, session_id: int) -> Optional[SlotSession]:
    """Obtiene una sesión por ID"""
    statement = select(SlotSession).where(SlotSession.id == session_id)
    return db.exec(statement).one_or_none()


def create_spin(
    db: Session,
    session: SlotSession,
    client_seed: str,
    bet_amount: float,
    lines: int = 1,
    user_id: Optional[int] = None
) -> SlotSpin:
    """
    Crea un nuevo spin con sistema provably fair.
    Calcula símbolos, multiplicador y ganancias.
    """
    if session.revealed:
        raise ValueError("Session already revealed")
    
    # Generar HMAC usando server seed + client seed + nonce
    nonce = session.nonce
    message = f"{client_seed}:{nonce}"
    hmac_hex = hmac_sha256_hex(session.server_seed, message)
    
    # Derivar símbolos del HMAC
    symbols = derive_symbols_from_hmac(hmac_hex)
    
    # Calcular multiplicador y ganancia
    multiplier = calculate_multiplier(symbols)
    win_amount = bet_amount * multiplier * lines if multiplier > 0 else 0.0
    
    print(f"🎲 SPIN: Símbolos={symbols} | Multiplicador={multiplier}x | Apuesta=${bet_amount} | Líneas={lines} | Ganancia=${win_amount}")
    
    # Crear registro del spin
    spin = SlotSpin(
        session_id=session.id,
        user_id=user_id,
        nonce=nonce,
        client_seed=client_seed,
        hmac_hex=hmac_hex,
        symbols=json.dumps(symbols),  # Guardar como JSON
        multiplier=multiplier,
        bet_amount=bet_amount,
        lines=lines,
        win_amount=win_amount,
        timestamp=datetime.now(timezone.utc)
    )
    
    db.add(spin)
    session.nonce += 1
    db.add(session)
    db.commit()
    db.refresh(spin)
    db.refresh(session)
    
    return spin


def create_test_spin(
    db: Session,
    session: SlotSession,
    client_seed: str,
    bet_amount: float,
    lines: int = 1,
    user_id: Optional[int] = None,
    forced_symbols: Optional[List[str]] = None
) -> SlotSpin:
    """
    FUNCIÓN DE TESTING - Permite forzar símbolos específicos
    Si forced_symbols es None, funciona como create_spin normal
    """
    if session.revealed:
        raise ValueError("Session already revealed")
    
    nonce = session.nonce
    message = f"{client_seed}:{nonce}"
    hmac_hex = hmac_sha256_hex(session.server_seed, message)
    
    # Si se fuerzan símbolos, usarlos; sino, derivar del HMAC
    if forced_symbols and len(forced_symbols) == 3:
        symbols = forced_symbols
        print(f"⚠️ TEST MODE: Forzando símbolos: {symbols}")
    else:
        symbols = derive_symbols_from_hmac(hmac_hex)
    
    # Calcular multiplicador y ganancia
    multiplier = calculate_multiplier(symbols)
    win_amount = bet_amount * multiplier * lines if multiplier > 0 else 0.0
    
    print(f"🎲 TEST SPIN: Símbolos={symbols} | Multiplicador={multiplier}x | Apuesta=${bet_amount} | Líneas={lines} | Ganancia=${win_amount}")
    
    spin = SlotSpin(
        session_id=session.id,
        user_id=user_id,
        nonce=nonce,
        client_seed=client_seed,
        hmac_hex=hmac_hex,
        symbols=json.dumps(symbols),
        multiplier=multiplier,
        bet_amount=bet_amount,
        lines=lines,
        win_amount=win_amount,
        timestamp=datetime.now(timezone.utc)
    )
    
    db.add(spin)
    session.nonce += 1
    db.add(session)
    db.commit()
    db.refresh(spin)
    db.refresh(session)
    
    return spin


def get_user_stats(db: Session, user_id: int) -> Dict[str, Any]:
    """Obtiene estadísticas del jugador"""
    # Total de spins
    total_spins = db.exec(
        select(func.count(SlotSpin.id)).where(SlotSpin.user_id == user_id)
    ).one()
    
    # Total ganado
    total_won = db.exec(
        select(func.sum(SlotSpin.win_amount)).where(
            SlotSpin.user_id == user_id,
            SlotSpin.win_amount > 0
        )
    ).one() or 0.0
    
    # Total apostado
    total_bet = db.exec(
        select(func.sum(SlotSpin.bet_amount)).where(SlotSpin.user_id == user_id)
    ).one() or 0.0
    
    # Mayor ganancia
    biggest_win_spin = db.exec(
        select(SlotSpin).where(SlotSpin.user_id == user_id)
        .order_by(SlotSpin.win_amount.desc())
    ).first()
    
    biggest_win = biggest_win_spin.win_amount if biggest_win_spin else 0.0
    
    return {
        "total_spins": total_spins or 0,
        "total_won": float(total_won),
        "total_lost": float(total_bet - total_won),
        "biggest_win": float(biggest_win)
    }


def reveal_session_seed(db: Session, session: SlotSession) -> str:
    """Revela el server seed de una sesión"""
    session.revealed = True
    db.add(session)
    db.commit()
    db.refresh(session)
    return session.server_seed


def update_user_balance(db: Session, user_id: int, amount: float) -> User:
    """Actualiza el saldo del usuario (puede ser positivo o negativo)"""
    statement = select(User).where(User.id == user_id)
    user = db.exec(statement).one_or_none()
    
    if not user:
        raise ValueError("User not found")
    
    user.saldo += amount
    
    # Actualizar estadísticas
    if amount > 0:
        user.ganancias_totales += amount
    else:
        user.perdidas_totales += abs(amount)
    
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user_balance_with_bet(
    db: Session,
    user_id: int,
    bet_amount: float,
    win_amount: float
) -> User:
    """Actualiza el saldo del usuario con apuesta y ganancia"""
    statement = select(User).where(User.id == user_id)
    user = db.exec(statement).one_or_none()
    
    if not user:
        raise ValueError("User not found")
    
    saldo_antes = user.saldo
    
    # Restar la apuesta
    user.saldo -= bet_amount
    
    # Sumar la ganancia si hay
    if win_amount > 0:
        user.saldo += win_amount
        user.ganancias_totales += win_amount
        print(f"🎰 GANANCIA! Usuario: {user.username} | Saldo antes: ${saldo_antes} | Apuesta: ${bet_amount} | Ganancia: ${win_amount} | Saldo después: ${user.saldo}")
    
    # Registrar la pérdida (apuesta perdida)
    if win_amount == 0:
        user.perdidas_totales += bet_amount
        print(f"❌ PÉRDIDA! Usuario: {user.username} | Saldo antes: ${saldo_antes} | Apuesta: ${bet_amount} | Saldo después: ${user.saldo}")
    elif win_amount < bet_amount:
        # Ganaste algo pero menos de lo que apostaste
        user.perdidas_totales += (bet_amount - win_amount)
    
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
