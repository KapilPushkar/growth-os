from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, require_team, verify_password
from app.database import get_db
from app.models import Client, User
from app.schemas import LoginIn
from app.serializers import user_out

router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["auth"])


def _me(db: Session, user: User) -> dict:
    data = user_out(user)
    client = db.get(Client, user.client_id) if user.client_id else None
    data["client"] = (
        {"id": client.id, "name": client.name, "company": client.company, "title": client.title}
        if client
        else None
    )
    return data


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)) -> dict:
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    return {"access_token": create_access_token(user), "token_type": "bearer", "user": _me(db, user)}


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return _me(db, user)


@users_router.get("")
def list_users(
    role: str | None = None,
    _: User = Depends(require_team),
    db: Session = Depends(get_db),
) -> list[dict]:
    query = select(User).order_by(User.role, User.name)
    if role:
        query = query.where(User.role == role)
    return [user_out(u) for u in db.scalars(query)]
