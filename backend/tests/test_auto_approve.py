from sqlalchemy import select

from app.database import SessionLocal
from app.models import ApprovalEvent
from app.services import process_auto_approvals
from tests.conftest import auth


def test_auto_approve_fires_after_threshold(api, db, make_user, make_client, make_content):
    admin = make_user("admin")
    client, _ = make_client(auto_approve_hours=48)
    overdue = make_content(client, status="client_review", hours_in_status=49)

    queues = api.get("/api/approvals", headers=auth(admin)).json()

    db.refresh(overdue)
    assert overdue.status == "approved"
    assert overdue.id not in {item["id"] for item in queues["client_review"]}
    event = db.scalars(select(ApprovalEvent).where(ApprovalEvent.content_id == overdue.id)).one()
    assert event.action == "auto_approve"
    assert event.user_id is None  # system action
    assert (event.from_status, event.to_status) == ("client_review", "approved")


def test_auto_approve_does_not_fire_before_threshold(api, db, make_user, make_client, make_content):
    admin = make_user("admin")
    client, _ = make_client(auto_approve_hours=48)
    recent = make_content(client, status="client_review", hours_in_status=47)

    queues = api.get("/api/approvals", headers=auth(admin)).json()

    db.refresh(recent)
    assert recent.status == "client_review"
    item = next(i for i in queues["client_review"] if i["id"] == recent.id)
    assert 0 < item["auto_approve_in_hours"] <= 1


def test_auto_approve_off_never_fires(api, db, make_user, make_client, make_content):
    admin = make_user("admin")
    client, _ = make_client(auto_approve_hours=0)
    old = make_content(client, status="client_review", hours_in_status=500)

    api.get("/api/dashboard", headers=auth(admin))

    db.refresh(old)
    assert old.status == "client_review"


def test_auto_approve_runs_from_content_list(api, db, make_client, make_content):
    client, client_user = make_client(auto_approve_hours=24)
    overdue = make_content(client, status="client_review", hours_in_status=30)

    items = api.get("/api/content", headers=auth(client_user)).json()

    assert next(i for i in items if i["id"] == overdue.id)["status"] == "approved"


def test_auto_approve_is_idempotent_across_sessions(db, make_client, make_content):
    client, _ = make_client(auto_approve_hours=24)
    overdue = make_content(client, status="client_review", hours_in_status=30)

    # Queues and dashboards evaluate auto-approve on every load, often in parallel.
    first, second = SessionLocal(), SessionLocal()
    try:
        assert process_auto_approvals(first) == 1
        assert process_auto_approvals(second) == 0
    finally:
        first.close()
        second.close()

    events = db.scalars(select(ApprovalEvent).where(ApprovalEvent.content_id == overdue.id)).all()
    assert [e.action for e in events] == ["auto_approve"]
