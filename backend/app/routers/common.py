"""Lookup helpers shared by routers; each one enforces tenant access."""

from typing import TypeVar

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import ensure_client_access
from app.database import Base
from app.models import CLIENT_HIDDEN_STATUSES, Client, ContentPiece, User

ModelT = TypeVar("ModelT", bound=Base)


def get_or_404(db: Session, model: type[ModelT], object_id: int) -> ModelT:
    instance = db.get(model, object_id)
    if instance is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{model.__name__} {object_id} not found")
    return instance


def load_client(db: Session, user: User, client_id: int) -> Client:
    ensure_client_access(user, client_id)
    return get_or_404(db, Client, client_id)


def load_owned(db: Session, user: User, model: type[ModelT], object_id: int) -> ModelT:
    """Fetch a client-owned row (anything with client_id) and check access to it."""
    instance = get_or_404(db, model, object_id)
    ensure_client_access(user, instance.client_id)  # type: ignore[attr-defined]
    return instance


def load_content(db: Session, user: User, content_id: int) -> ContentPiece:
    piece = load_owned(db, user, ContentPiece, content_id)
    # Internal drafts are invisible to clients rather than forbidden.
    if not user.is_team and piece.status in CLIENT_HIDDEN_STATUSES:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"ContentPiece {content_id} not found")
    return piece


def client_names(db: Session) -> dict[int, str]:
    return dict(db.execute(select(Client.id, Client.name)).tuples().all())


def client_brief(client: Client) -> dict:
    return {"id": client.id, "name": client.name, "title": client.title, "company": client.company}
