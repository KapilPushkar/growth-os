from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_team, scope_client_id
from app.database import get_db
from app.models import TEAM_ROLES, Client, ContentPiece, User
from app.routers.common import load_client
from app.schemas import ClientCreate, ClientUpdate, OnboardingUpdate
from app.serializers import client_out
from app.services import create_client, health_score, log_activity, set_onboarding_step

router = APIRouter(prefix="/clients", tags=["clients"])

# What a client may change about their own account from the portal.
CLIENT_EDITABLE_FIELDS = {
    "brand_voice",
    "tone_tags",
    "target_audience",
    "content_pillars",
    "topics_to_avoid",
    "goals",
    "auto_approve_hours",
}


def _team_names(db: Session) -> dict[int, str]:
    rows = db.execute(select(User.id, User.name).where(User.role.in_(TEAM_ROLES)))
    return dict(rows.tuples().all())


def _client_detail(db: Session, client: Client, managers: dict[int, str]) -> dict:
    data = client_out(client)
    data["account_manager"] = (
        {"id": client.account_manager_id, "name": managers.get(client.account_manager_id)}
        if client.account_manager_id
        else None
    )
    data["health"] = health_score(db, client)
    data["approvals_waiting"] = db.scalar(
        select(func.count(ContentPiece.id)).where(
            ContentPiece.client_id == client.id, ContentPiece.status == "client_review"
        )
    ) or 0
    return data


@router.get("")
def list_clients(
    status_filter: str | None = Query(default=None, alias="status"),
    q: str | None = None,
    industry: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    query = select(Client).order_by(Client.name)
    client_id = scope_client_id(user, None)
    if client_id is not None:
        query = query.where(Client.id == client_id)
    if status_filter:
        query = query.where(Client.status == status_filter)
    if industry:
        query = query.where(Client.industry == industry)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(or_(Client.name.ilike(pattern), Client.company.ilike(pattern)))
    managers = _team_names(db)
    return [_client_detail(db, c, managers) for c in db.scalars(query)]


@router.post("", status_code=status.HTTP_201_CREATED)
def create(
    body: ClientCreate, user: User = Depends(require_team), db: Session = Depends(get_db)
) -> dict:
    client, login, temp_password = create_client(db, body.model_dump(), user)
    db.commit()
    return {
        "client": _client_detail(db, client, _team_names(db)),
        # Shown once; only the hash is stored.
        "login": {"email": login.email, "temp_password": temp_password} if login else None,
    }


@router.get("/{client_id}")
def get_client(
    client_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    return _client_detail(db, load_client(db, user, client_id), _team_names(db))


@router.patch("/{client_id}")
def update_client(
    client_id: int,
    body: ClientUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    client = load_client(db, user, client_id)
    changes = body.model_dump(exclude_unset=True)
    if not user.is_team:
        blocked = sorted(set(changes) - CLIENT_EDITABLE_FIELDS)
        if blocked:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, f"Clients cannot change: {', '.join(blocked)}"
            )
    manager_id = changes.get("account_manager_id")
    if manager_id is not None:
        manager = db.get(User, manager_id)
        if manager is None or not manager.is_team:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Account manager must be a team member")
    for field, value in changes.items():
        setattr(client, field, value)
    if changes:
        log_activity(db, client.id, user, "client.updated", f"{user.name} updated the profile for {client.name}")
    db.commit()
    return _client_detail(db, client, _team_names(db))


@router.post("/{client_id}/onboarding")
def update_onboarding(
    client_id: int,
    body: OnboardingUpdate,
    user: User = Depends(require_team),
    db: Session = Depends(get_db),
) -> dict:
    client = load_client(db, user, client_id)
    set_onboarding_step(db, client, body.step, body.done, user)
    db.commit()
    return _client_detail(db, client, _team_names(db))
