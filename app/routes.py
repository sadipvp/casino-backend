from fastapi import APIRouter

router = APIRouter(prefix="/games", tags=["Games"])


@router.get("/")
def list_games():
    return {"games": ["ruleta", "blackjack", "tragamonedas"]}


@router.post("/bet")
def make_bet(amount: float, game: str) -> dict[str, str | float]:
    return {"status": "ok", "amount": amount, "game": game}
