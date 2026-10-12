from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.analytics import lead_summary
from app.auth import get_current_user, require_team, scope_client_id
from app.database import get_db
from app.models import LEAD_STAGES, ContentPiece, Lead, User
from app.routers.common import client_names, load_client, load_owned
from app.schemas import LeadCreate, LeadUpdate
from app.serializers import lead_out
from app.services import change_lead_stage, log_activity, validate_lead_links

router = APIRouter(prefix="/leads", tags=["leads"])

# Clients can keep notes on their leads; everything else is run by the team.
CLIENT_EDITABLE_FIELDS = {"notes"}


def _leads(
    db: Session,
    client_id: int | None,
    *,
    stage: str | None = None,
    source: str | None = None,
    campaign_id: int | None = None,
    q: str | None = None,
) -> list[Lead]:
    query = select(Lead).order_by(Lead.updated_at.desc())
    if client_id is not None:
        query = query.where(Lead.client_id == client_id)
    if stage:
        query = query.where(Lead.stage == stage)
    if source:
        query = query.where(Lead.source == source)
    if campaign_id is not None:
        query = query.where(Lead.campaign_id == campaign_id)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(or_(Lead.name.ilike(pattern), Lead.company.ilike(pattern)))
    return list(db.scalars(query))


def _with_client(leads: list[Lead], names: dict[int, str]) -> list[dict]:
    return [{**lead_out(lead), "client_name": names.get(lead.client_id)} for lead in leads]


@router.get("")
def list_leads(
    client_id: int | None = None,
    stage: str | None = None,
    source: str | None = None,
    campaign_id: int | None = None,
    q: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    client_id = scope_client_id(user, client_id)
    leads = _leads(db, client_id, stage=stage, source=source, campaign_id=campaign_id, q=q)
    return _with_client(leads, client_names(db))


@router.get("/pipeline")
def pipeline(
    client_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    client_id = scope_client_id(user, client_id)
    leads = _leads(db, client_id)
    names = client_names(db)
    return {
        "stages": [
            {
                "stage": stage,
                "leads": _with_client([lead for lead in leads if lead.stage == stage], names),
                "value": sum(lead.deal_value for lead in leads if lead.stage == stage),
            }
            for stage in LEAD_STAGES
        ],
        "summary": lead_summary(db, client_id),
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_lead(
    body: LeadCreate, user: User = Depends(require_team), db: Session = Depends(get_db)
) -> dict:
    client = load_client(db, user, body.client_id)
    validate_lead_links(db, body.client_id, body.campaign_id, body.content_id)
    lead = Lead(**body.model_dump())
    db.add(lead)
    if lead.content_id is not None:
        db.get(ContentPiece, lead.content_id).leads_generated += 1
    log_activity(
        db, client.id, user, "lead.created", f"{user.name} added lead {lead.name} ({lead.company or 'no company'})"
    )
    db.commit()
    return lead_out(lead)


@router.patch("/{lead_id}")
def update_lead(
    lead_id: int,
    body: LeadUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    lead = load_owned(db, user, Lead, lead_id)
    changes = body.model_dump(exclude_unset=True)
    if not user.is_team:
        blocked = sorted(set(changes) - CLIENT_EDITABLE_FIELDS)
        if blocked:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, f"Clients cannot change: {', '.join(blocked)}"
            )
    validate_lead_links(db, lead.client_id, changes.get("campaign_id"), changes.get("content_id"))
    stage = changes.pop("stage", None)
    for field, value in changes.items():
        setattr(lead, field, value)
    if stage is not None:
        change_lead_stage(db, lead, stage, user)
    db.commit()
    return lead_out(lead)


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(
    lead_id: int, user: User = Depends(require_team), db: Session = Depends(get_db)
) -> Response:
    db.delete(load_owned(db, user, Lead, lead_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
