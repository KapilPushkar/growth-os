import random
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_team, scope_client_id
from app.database import get_db
from app.models import CLIENT_HIDDEN_STATUSES, Campaign, Client, ContentPiece, User, to_naive_utc
from app.routers.common import client_brief, client_names, get_or_404, load_client, load_content
from app.schemas import BulkTransitionIn, ContentCreate, ContentUpdate, TransitionIn
from app.serializers import content_out
from app.services import (
    DomainError,
    allowed_actions,
    apply_transition,
    log_activity,
    process_auto_approvals,
    record_event,
    simulate_metrics_sync,
    waiting_hours,
)

router = APIRouter(prefix="/content", tags=["content"])
approvals_router = APIRouter(prefix="/approvals", tags=["approvals"])


def _detail(db: Session, piece: ContentPiece, user: User) -> dict:
    data = content_out(piece, events=True, allowed_actions=allowed_actions(piece, user))
    data["client"] = client_brief(get_or_404(db, Client, piece.client_id))
    return data


def _check_campaign(db: Session, client_id: int, campaign_id: int | None) -> None:
    if campaign_id is None:
        return
    campaign = db.get(Campaign, campaign_id)
    if campaign is None or campaign.client_id != client_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Campaign does not belong to this client")


@router.get("")
def list_content(
    client_id: int | None = None,
    status_filter: str | None = Query(default=None, alias="status", description="Comma-separated"),
    channel: str | None = None,
    campaign_id: int | None = None,
    date_from: datetime | None = Query(default=None, description="Scheduled/published on or after"),
    date_to: datetime | None = Query(default=None, description="Scheduled/published before"),
    q: str | None = None,
    limit: int = Query(default=500, ge=1, le=2000),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    client_id = scope_client_id(user, client_id)
    process_auto_approvals(db, client_id)

    query = select(ContentPiece).order_by(ContentPiece.updated_at.desc()).limit(limit)
    if client_id is not None:
        query = query.where(ContentPiece.client_id == client_id)
    if not user.is_team:
        query = query.where(ContentPiece.status.not_in(CLIENT_HIDDEN_STATUSES))
    if status_filter:
        query = query.where(ContentPiece.status.in_(status_filter.split(",")))
    if channel:
        query = query.where(ContentPiece.channel == channel)
    if campaign_id is not None:
        query = query.where(ContentPiece.campaign_id == campaign_id)
    when = func.coalesce(ContentPiece.published_at, ContentPiece.scheduled_at)
    if date_from is not None:
        query = query.where(when >= to_naive_utc(date_from))
    if date_to is not None:
        query = query.where(when < to_naive_utc(date_to))
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(or_(ContentPiece.title.ilike(pattern), ContentPiece.body.ilike(pattern)))

    names = client_names(db)
    items = []
    for piece in db.scalars(query):
        item = content_out(piece)
        item["client_name"] = names.get(piece.client_id)
        items.append(item)
    return items


@router.post("", status_code=status.HTTP_201_CREATED)
def create_content(
    body: ContentCreate, user: User = Depends(require_team), db: Session = Depends(get_db)
) -> dict:
    load_client(db, user, body.client_id)
    _check_campaign(db, body.client_id, body.campaign_id)
    piece = ContentPiece(**body.model_dump(), created_by_id=user.id)
    db.add(piece)
    db.flush()
    record_event(db, piece, user, "create", None, piece.status)
    db.commit()
    return _detail(db, piece, user)


@router.post("/bulk-transition")
def bulk_transition(
    body: BulkTransitionIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    done, errors = [], []
    for content_id in dict.fromkeys(body.ids):
        try:
            piece = load_content(db, user, content_id)
            apply_transition(
                db, piece, body.action, user, body.note, to_naive_utc(body.scheduled_at)
            )
            done.append(content_out(piece))
        except HTTPException as exc:
            errors.append({"id": content_id, "status_code": exc.status_code, "detail": exc.detail})
        except DomainError as exc:
            errors.append({"id": content_id, "status_code": exc.status_code, "detail": exc.detail})
    db.commit()
    return {"done": done, "errors": errors}


@router.get("/{content_id}")
def get_content(
    content_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    return _detail(db, load_content(db, user, content_id), user)


@router.patch("/{content_id}")
def update_content(
    content_id: int,
    body: ContentUpdate,
    user: User = Depends(require_team),
    db: Session = Depends(get_db),
) -> dict:
    piece = load_content(db, user, content_id)
    changes = body.model_dump(exclude_unset=True)
    if "campaign_id" in changes:
        _check_campaign(db, piece.client_id, changes["campaign_id"])
    for field, value in changes.items():
        setattr(piece, field, value)
    db.commit()
    return _detail(db, piece, user)


@router.delete("/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_content(
    content_id: int, user: User = Depends(require_team), db: Session = Depends(get_db)
) -> Response:
    piece = load_content(db, user, content_id)
    log_activity(db, piece.client_id, user, "content.deleted", f"{user.name} deleted “{piece.title or 'Untitled'}”")
    db.delete(piece)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{content_id}/transition")
def transition(
    content_id: int,
    body: TransitionIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    piece = load_content(db, user, content_id)
    apply_transition(db, piece, body.action, user, body.note, to_naive_utc(body.scheduled_at))
    db.commit()
    return _detail(db, piece, user)


@router.post("/{content_id}/sync-metrics")
def sync_metrics(
    content_id: int, user: User = Depends(require_team), db: Session = Depends(get_db)
) -> dict:
    piece = load_content(db, user, content_id)
    delta = simulate_metrics_sync(piece, random.Random())
    log_activity(db, piece.client_id, user, "content.metrics", f"Metrics synced for “{piece.title}” (+{delta['impressions']:,} impressions)")
    db.commit()
    return {
        "item": _detail(db, piece, user),
        "delta": delta,
        "method": "simulated",
        "note": "Simulated metrics: no LinkedIn/X analytics integration yet.",
    }


@approvals_router.get("")
def approvals(
    client_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    client_id = scope_client_id(user, client_id)
    process_auto_approvals(db, client_id)

    buckets = ("internal_review", "client_review", "changes_requested")
    visible = buckets if user.is_team else ("client_review", "changes_requested")
    query = (
        select(ContentPiece)
        .where(ContentPiece.status.in_(visible))
        .order_by(ContentPiece.status_changed_at)
    )
    if client_id is not None:
        query = query.where(ContentPiece.client_id == client_id)

    clients = {c.id: c for c in db.scalars(select(Client))}
    result: dict[str, list] = {bucket: [] for bucket in buckets}
    for piece in db.scalars(query):
        item = content_out(piece, allowed_actions=allowed_actions(piece, user))
        item["client"] = client_brief(clients[piece.client_id])
        item["waiting_hours"] = waiting_hours(piece)
        auto = clients[piece.client_id].auto_approve_hours
        item["auto_approve_in_hours"] = (
            round(max(0.0, auto - item["waiting_hours"]), 1)
            if auto and piece.status == "client_review"
            else None
        )
        result[piece.status].append(item)
    return result
