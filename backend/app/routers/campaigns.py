from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_team, scope_client_id
from app.database import get_db
from app.models import Campaign, User
from app.routers.common import load_client, load_owned
from app.schemas import CampaignCreate, CampaignUpdate
from app.serializers import campaign_out
from app.services import DomainError, campaign_progress, log_activity

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


def _out(db: Session, campaign: Campaign) -> dict:
    return campaign_out(campaign, campaign_progress(db, campaign))


def _check_dates(campaign: Campaign) -> None:
    if campaign.start_date and campaign.end_date and campaign.end_date < campaign.start_date:
        raise DomainError("End date must be on or after the start date")


@router.get("")
def list_campaigns(
    client_id: int | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    type_filter: str | None = Query(default=None, alias="type"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    client_id = scope_client_id(user, client_id)
    query = select(Campaign).order_by(Campaign.start_date.desc())
    if client_id is not None:
        query = query.where(Campaign.client_id == client_id)
    if status_filter:
        query = query.where(Campaign.status == status_filter)
    if type_filter:
        query = query.where(Campaign.type == type_filter)
    return [_out(db, c) for c in db.scalars(query)]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_campaign(
    body: CampaignCreate, user: User = Depends(require_team), db: Session = Depends(get_db)
) -> dict:
    load_client(db, user, body.client_id)
    campaign = Campaign(**body.model_dump())
    _check_dates(campaign)
    db.add(campaign)
    log_activity(
        db, body.client_id, user, "campaign.created", f"{user.name} created campaign “{campaign.name}”"
    )
    db.commit()
    return _out(db, campaign)


@router.get("/{campaign_id}")
def get_campaign(
    campaign_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    return _out(db, load_owned(db, user, Campaign, campaign_id))


@router.patch("/{campaign_id}")
def update_campaign(
    campaign_id: int,
    body: CampaignUpdate,
    user: User = Depends(require_team),
    db: Session = Depends(get_db),
) -> dict:
    campaign = load_owned(db, user, Campaign, campaign_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(campaign, field, value)
    _check_dates(campaign)
    db.commit()
    return _out(db, campaign)


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign(
    campaign_id: int, user: User = Depends(require_team), db: Session = Depends(get_db)
) -> Response:
    campaign = load_owned(db, user, Campaign, campaign_id)
    log_activity(
        db, campaign.client_id, user, "campaign.deleted", f"{user.name} deleted campaign “{campaign.name}”"
    )
    db.delete(campaign)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
