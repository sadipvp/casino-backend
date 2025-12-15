# app/admin/routes.py
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from typing import Optional, List

from sqlmodel import Session

from app.database import get_session
from app.admin import service as admin_service
from app.model import CreditRequest, User
from fastapi.security import OAuth2PasswordBearer
from app.auth.services import get_user_from_token

router = APIRouter(prefix="/v1/admin", tags=["admin"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

class CreateCreditReqIn(BaseModel):
    amount: float
    note: Optional[str] = None

class CreateCreditReqOut(BaseModel):
    id: int
    user_id: int
    amount: float
    status: str

class ApproveDenyIn(BaseModel):
    note: Optional[str] = None

@router.post("/credits", response_model=CreateCreditReqOut)
def create_request_for_user(payload: CreateCreditReqIn, token: str = Depends(oauth2_scheme), db: Session = Depends(get_session)):
    # permitimos crear solicitud solo para el propio usuario (o admin si quieres)
    user = get_user_from_token(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    req = admin_service.create_credit_request(db, user.id, payload.amount, payload.note)
    return CreateCreditReqOut(id=req.id, user_id=req.user_id, amount=req.amount, status=req.status)

@router.get("/credits", response_model=List[dict])
def list_credits(status: Optional[str] = None, token: str = Depends(oauth2_scheme), db: Session = Depends(get_session)):
    # solo admins pueden listar todas; si un jugador pide listado solo devuelve sus solicitudes
    user = get_user_from_token(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")

    is_admin = (user.role and user.role.lower() in ("admin", "administrator", "administrador"))
    reqs = admin_service.list_credit_requests(db, status=status)
    out = []
    for r in reqs:
        if not is_admin and r.user_id != user.id:
            continue
        # Obtener username del usuario que solicita
        req_user = db.get(User, r.user_id)
        username = req_user.username if req_user else None
        
        out.append({
            "id": r.id,
            "user_id": r.user_id,
            "username": username,
            "amount": r.amount,
            "status": r.status,
            "created_at": r.created_at.isoformat(),
            "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
            "reviewer_id": r.reviewer_id,
            "note": r.note
        })
    return out

@router.post("/credits/{request_id}/approve")
def approve_credit(request_id: int, token: str = Depends(oauth2_scheme), db: Session = Depends(get_session), payload: Optional[ApproveDenyIn] = Body(None)):
    user = get_user_from_token(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    # require admin
    if not (user.role and user.role.lower() in ("admin", "administrator", "administrador")):
        raise HTTPException(status_code=403, detail="Require admin role")

    try:
        req = admin_service.approve_credit_request(db, request_id, user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": req.id, "status": req.status, "user_id": req.user_id, "amount": req.amount, "reviewed_at": req.reviewed_at.isoformat()}

@router.post("/credits/{request_id}/deny")
def deny_credit(request_id: int, token: str = Depends(oauth2_scheme), db: Session = Depends(get_session), payload: Optional[ApproveDenyIn] = Body(None)):
    user = get_user_from_token(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    # require admin
    if not (user.role and user.role.lower() in ("admin", "administrator", "administrador")):
        raise HTTPException(status_code=403, detail="Require admin role")
    try:
        req = admin_service.deny_credit_request(db, request_id, user.id, payload.note if payload else None)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": req.id, "status": req.status, "user_id": req.user_id, "amount": req.amount, "reviewed_at": req.reviewed_at.isoformat()}
