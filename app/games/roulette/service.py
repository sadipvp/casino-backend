# app/roulette/service.py
import secrets
import hashlib
import hmac
import json
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from sqlmodel import Session, select
from app.model import RouletteSession, Spin, User

# --- wheel & colors (EUROPEAN only) ---
EUROPEAN_POCKETS = list(range(0, 37))
RED_NUMS = {
    1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36
}
BLACK_NUMS = set(range(1,37)) - RED_NUMS

def pocket_color(pocket) -> str:
    if pocket == 0:
        return "green"
    if pocket in RED_NUMS:
        return "red"
    if pocket in BLACK_NUMS:
        return "black"
    return "unknown"

# ---- provably fair helpers ----
def generate_server_seed() -> str:
    return secrets.token_hex(32)

def hash_server_seed(server_seed: str) -> str:
    return hashlib.sha256(server_seed.encode()).hexdigest()

def hmac_sha256_hex(key_hex: str, message: str) -> str:
    key = bytes.fromhex(key_hex)
    hm = hmac.new(key, message.encode(), hashlib.sha256)
    return hm.hexdigest()

def derive_integer_from_hex(hexstr: str) -> int:
    return int(hexstr, 16)

# ---- DB operations (public API expected by routes) ----
def create_session(db: Session) -> RouletteSession:
    server_seed = generate_server_seed()
    session = RouletteSession(
        server_seed=server_seed,
        server_seed_hash=hash_server_seed(server_seed),
        nonce=0,
        revealed=False
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

def get_session(db: Session, session_id: int) -> Optional[RouletteSession]:
    statement = select(RouletteSession).where(RouletteSession.id == session_id)
    return db.exec(statement).one_or_none()

def create_spin(db: Session, session: RouletteSession, client_seed: str) -> Spin:
    if session.revealed:
        raise ValueError("Session already revealed")

    nonce = session.nonce
    message = f"{client_seed}:{nonce}"
    hmac_hex = hmac_sha256_hex(session.server_seed, message)
    number = derive_integer_from_hex(hmac_hex)
    index = number % len(EUROPEAN_POCKETS)
    pocket = EUROPEAN_POCKETS[index]
    color = pocket_color(pocket)

    spin = Spin(
        session_id=session.id,
        nonce=nonce,
        client_seed=client_seed,
        hmac_hex=hmac_hex,
        pocket=pocket,
        color=color,
        timestamp=datetime.now(timezone.utc)
    )

    db.add(spin)
    session.nonce += 1
    db.add(session)
    db.commit()
    db.refresh(spin)
    db.refresh(session)
    return spin

def list_spins(db: Session, session: RouletteSession):
    statement = select(Spin).where(Spin.session_id == session.id).order_by(Spin.nonce)
    return db.exec(statement).all()

def reveal_session_seed(db: Session, session: RouletteSession):
    session.revealed = True
    db.add(session)
    db.commit()
    db.refresh(session)
    return session.server_seed

# ---- EVALUATE BETS (same rules as earlier) ----
PAYOUTS = {
    "straight": 35,
    "color": 1,
    "odd_even": 1,
    "low_high": 1,
    "dozen": 2,
    "column": 2,
}

col1 = {1,4,7,10,13,16,19,22,25,28,31,34}
col2 = {2,5,8,11,14,17,20,23,26,29,32,35}
col3 = {3,6,9,12,15,18,21,24,27,30,33,36}

def evaluate_bet(bet: Dict[str,Any], spin: Spin) -> (bool, float):
    pocket = spin.pocket
    amount = float(bet.get("amount", 0))
    t = bet.get("type")
    if t == "straight":
        target = bet["number"]
        if pocket == target:
            return True, amount * PAYOUTS["straight"]
        else:
            return False, -amount
    if t == "color":
        side = bet["side"].lower()
        if pocket == 0:
            return False, -amount
        if pocket_color(pocket) == side:
            return True, amount * PAYOUTS["color"]
        else:
            return False, -amount
    if t == "odd_even":
        side = bet["side"].lower()
        if pocket == 0:
            return False, -amount
        if side == "odd" and (int(pocket) % 2 == 1):
            return True, amount * PAYOUTS["odd_even"]
        if side == "even" and (int(pocket) % 2 == 0):
            return True, amount * PAYOUTS["odd_even"]
        return False, -amount
    if t == "low_high":
        side = bet["side"].lower()
        if pocket == 0:
            return False, -amount
        n = int(pocket)
        if side == "low" and 1 <= n <= 18:
            return True, amount * PAYOUTS["low_high"]
        if side == "high" and 19 <= n <= 36:
            return True, amount * PAYOUTS["low_high"]
        return False, -amount
    if t == "dozen":
        which = int(bet["which"])
        if pocket == 0:
            return False, -amount
        n = int(pocket)
        if which == 1 and 1 <= n <= 12:
            return True, amount * PAYOUTS["dozen"]
        if which == 2 and 13 <= n <= 24:
            return True, amount * PAYOUTS["dozen"]
        if which == 3 and 25 <= n <= 36:
            return True, amount * PAYOUTS["dozen"]
        return False, -amount
    if t == "column":
        which = int(bet["which"])
        if pocket == 0:
            return False, -amount
        n = int(pocket)
        if which == 1 and n in col1:
            return True, amount * PAYOUTS["column"]
        if which == 2 and n in col2:
            return True, amount * PAYOUTS["column"]
        if which == 3 and n in col3:
            return True, amount * PAYOUTS["column"]
        return False, -amount
    raise ValueError("Unsupported bet type")

# ---- CREATE A BET (atomic-ish: create spin -> evaluate -> update user & spin) ----
def create_bet(db: Session, session: RouletteSession, username: str, bet: Dict[str,Any], client_seed: str):
    """
    1) check session exists & not revealed
    2) find user by username
    3) ensure user has enough saldo
    4) create spin (provably fair)
    5) evaluate bet, update user.saldo and stats, update spin with bet info
    """
    if session.revealed:
        raise ValueError("Session already revealed")

    # get user
    stmt = select(User).where(User.username == username)
    user = db.exec(stmt).one_or_none()
    if not user:
        raise ValueError("User not found")

    amount = float(bet.get("amount", 0))
    if amount <= 0:
        raise ValueError("Invalid amount")

    if user.saldo < amount:
        raise ValueError("Insufficient balance")

    # create spin
    spin = create_spin(db, session, client_seed)

    # evaluate
    won, payout = evaluate_bet(bet, spin)  # payout is net (positive if win, negative stake if lose)

    # update user balances and stats
    # if payout > 0: user gains payout, otherwise subtract stake (but stake already removed below)
    # define accounting: we will subtract stake first, then add payout if positive
    user.saldo -= amount
    if payout > 0:
        user.saldo += (amount + payout) - amount  # payout is net win; simplify: user.saldo += payout
        # but payout already expresses net win, so add payout
        # Net accounting: start -amount, then + (amount + payout) ? to avoid duplication, better:
        # We'll implement: user.saldo += payout
    # but to be clear, do:
    user.saldo += payout  # payout is positive for win, negative for loss
    # update statistics
    if payout >= 0:
        user.ganancias_totales = (user.ganancias_totales or 0) + max(payout, 0)
    else:
        user.perdidas_totales = (user.perdidas_totales or 0) + (-payout)

    # attach bet data to spin
    spin.user_id = user.id
    spin.bet_type = bet.get("type")
    spin.bet_payload = json.dumps({k: v for k, v in bet.items() if k != "amount"})
    spin.bet_amount = amount
    spin.payout = payout

    db.add(user)
    db.add(spin)
    db.commit()
    db.refresh(user)
    db.refresh(spin)

    return {
        "spin": {
            "nonce": spin.nonce,
            "pocket": spin.pocket,
            "color": spin.color,
            "hmac_hex": spin.hmac_hex
        },
        "bet_result": {
            "won": bool(payout > 0),
            "payout": payout
        },
        "user": {
            "id": user.id,
            "username": user.username,
            "saldo": user.saldo,
            "ganancias_totales": user.ganancias_totales,
            "perdidas_totales": user.perdidas_totales
        }
    }
