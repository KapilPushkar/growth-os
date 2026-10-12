from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import ai, analytics
from app.auth import get_current_user, require_team
from app.database import get_db
from app.models import User
from app.routers.common import load_client
from app.services import process_auto_approvals

router = APIRouter(tags=["analytics"])


@router.get("/dashboard")
def dashboard(_: User = Depends(require_team), db: Session = Depends(get_db)) -> dict:
    process_auto_approvals(db)
    return analytics.dashboard(db)


@router.get("/clients/{client_id}/impact")
def impact(
    client_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    return analytics.impact(db, load_client(db, user, client_id))


@router.get("/clients/{client_id}/report")
def report(
    client_id: int,
    days: int = Query(default=30, ge=7, le=365),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    client = load_client(db, user, client_id)
    data = analytics.report(db, client, days)
    summary, source = ai.report_summary(client, data)
    return {**data, **summary, "summary_source": source}
