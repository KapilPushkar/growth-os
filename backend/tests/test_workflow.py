"""The approval state machine, enforced on the server."""

import pytest
from sqlalchemy import select

from app.models import Activity, ApprovalEvent
from app.services import TRANSITIONS
from tests.conftest import auth


def transition(api, user, piece_id, action, **extra):
    return api.post(
        f"/api/content/{piece_id}/transition", headers=auth(user), json={"action": action, **extra}
    )


@pytest.fixture
def setup(make_user, make_client, make_content):
    team = make_user("strategist")
    client, client_user = make_client()
    return team, client, client_user, make_content


def test_happy_path_draft_to_published(api, db, setup):
    team, client, client_user, make_content = setup
    piece = make_content(client, status="draft")

    steps = [
        (team, "submit", {}, "internal_review"),
        (team, "send_to_client", {}, "client_review"),
        (client_user, "approve", {}, "approved"),
        (team, "schedule", {"scheduled_at": "2030-01-15T09:00:00Z"}, "scheduled"),
        (team, "publish", {}, "published"),
    ]
    for user, action, extra, expected in steps:
        response = transition(api, user, piece.id, action, **extra)
        assert response.status_code == 200, (action, response.json())
        assert response.json()["status"] == expected

    detail = api.get(f"/api/content/{piece.id}", headers=auth(team)).json()
    assert detail["published_at"] is not None
    assert detail["scheduled_at"] == "2030-01-15T09:00:00Z"
    assert [(e["action"], e["from_status"], e["to_status"]) for e in detail["events"]] == [
        ("submit", "draft", "internal_review"),
        ("send_to_client", "internal_review", "client_review"),
        ("approve", "client_review", "approved"),
        ("schedule", "approved", "scheduled"),
        ("publish", "scheduled", "published"),
    ]
    assert detail["events"][2]["user"]["role"] == "client"
    activities = db.scalars(select(Activity).where(Activity.client_id == client.id)).all()
    assert len(activities) == 5


@pytest.mark.parametrize(
    ("status", "action"),
    [
        ("draft", "approve"),
        ("draft", "publish"),
        ("client_review", "submit"),
        ("published", "schedule"),
        ("approved", "revise"),
        ("draft", "reject_internal"),
    ],
)
def test_invalid_from_status_is_409(api, setup, status, action):
    team, client, _, make_content = setup
    piece = make_content(client, status=status)

    response = transition(api, team, piece.id, action, scheduled_at="2030-01-01T00:00:00Z")

    assert response.status_code == 409


def test_client_cannot_publish(api, setup):
    _, client, client_user, make_content = setup
    piece = make_content(client, status="approved")

    response = transition(api, client_user, piece.id, "publish")

    assert response.status_code == 403


def test_client_cannot_use_team_actions(api, setup):
    _, client, client_user, make_content = setup
    piece = make_content(client, status="changes_requested")

    assert transition(api, client_user, piece.id, "revise").status_code == 403


def test_request_changes_requires_a_note(api, setup):
    _, client, client_user, make_content = setup
    piece = make_content(client, status="client_review")

    missing = transition(api, client_user, piece.id, "request_changes")
    blank = transition(api, client_user, piece.id, "request_changes", note="   ")
    ok = transition(api, client_user, piece.id, "request_changes", note="Shorter hook please")

    assert missing.status_code == 400
    assert blank.status_code == 400
    assert ok.status_code == 200
    assert ok.json()["status"] == "changes_requested"
    assert ok.json()["events"][-1]["note"] == "Shorter hook please"


def test_schedule_requires_a_date(api, setup):
    team, client, _, make_content = setup
    piece = make_content(client, status="approved")

    assert transition(api, team, piece.id, "schedule").status_code == 400


def test_unknown_action_is_400(api, setup):
    team, client, _, make_content = setup
    piece = make_content(client, status="draft")

    assert transition(api, team, piece.id, "teleport").status_code == 400


def test_comment_records_event_without_changing_status(api, db, setup):
    _, client, client_user, make_content = setup
    piece = make_content(client, status="client_review")

    response = transition(api, client_user, piece.id, "comment", note="Love it")

    assert response.json()["status"] == "client_review"
    event = db.scalars(select(ApprovalEvent).where(ApprovalEvent.content_id == piece.id)).one()
    assert (event.action, event.note) == ("comment", "Love it")


def test_allowed_actions_reflect_status_and_role(api, setup):
    team, client, client_user, make_content = setup
    piece = make_content(client, status="client_review")

    team_view = api.get(f"/api/content/{piece.id}", headers=auth(team)).json()["allowed_actions"]
    client_view = api.get(f"/api/content/{piece.id}", headers=auth(client_user)).json()["allowed_actions"]

    assert set(team_view) == {"approve", "request_changes", "comment"}
    assert set(client_view) == {"approve", "request_changes", "comment"}
    draft = make_content(client, status="draft")
    assert "publish" not in api.get(f"/api/content/{draft.id}", headers=auth(team)).json()["allowed_actions"]


def test_bulk_approve_reports_done_and_errors(api, setup):
    _, client, client_user, make_content = setup
    waiting = [make_content(client, status="client_review") for _ in range(2)]
    published = make_content(client, status="published")

    response = api.post(
        "/api/content/bulk-transition",
        headers=auth(client_user),
        json={"ids": [p.id for p in waiting] + [published.id, 999999], "action": "approve"},
    )

    body = response.json()
    assert response.status_code == 200
    assert {item["id"] for item in body["done"]} == {p.id for p in waiting}
    assert {e["id"]: e["status_code"] for e in body["errors"]} == {published.id: 409, 999999: 404}


def test_transition_table_matches_documented_actions():
    assert set(TRANSITIONS) == {
        "submit",
        "send_to_client",
        "reject_internal",
        "approve",
        "request_changes",
        "revise",
        "schedule",
        "publish",
        "comment",
    }
