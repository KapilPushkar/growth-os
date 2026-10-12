"""Client users can only ever see and touch their own account."""

import pytest

from app.models import Lead
from tests.conftest import auth


@pytest.fixture
def two_clients(db, make_client, make_content):
    client_a, user_a = make_client("Asha Alpha")
    client_b, user_b = make_client("Ben Beta")
    piece_b = make_content(client_b, status="client_review")
    lead_b = Lead(client_id=client_b.id, name="Prospect B", company="B Corp")
    db.add(lead_b)
    db.commit()
    return {"a": (client_a, user_a), "b": (client_b, user_b), "piece_b": piece_b, "lead_b": lead_b}


def test_client_cannot_read_another_client(api, two_clients):
    _, user_a = two_clients["a"]
    client_b, _ = two_clients["b"]
    headers = auth(user_a)

    assert api.get(f"/api/clients/{client_b.id}", headers=headers).status_code == 403
    assert api.get(f"/api/clients/{client_b.id}/impact", headers=headers).status_code == 403
    assert api.get(f"/api/clients/{client_b.id}/report", headers=headers).status_code == 403
    assert api.patch(f"/api/clients/{client_b.id}", headers=headers, json={"brand_voice": "x"}).status_code == 403


def test_client_cannot_read_or_act_on_another_clients_content(api, two_clients):
    _, user_a = two_clients["a"]
    client_b, _ = two_clients["b"]
    piece_b = two_clients["piece_b"]
    headers = auth(user_a)

    assert api.get(f"/api/content?client_id={client_b.id}", headers=headers).status_code == 403
    assert api.get(f"/api/content/{piece_b.id}", headers=headers).status_code == 403
    approve = api.post(f"/api/content/{piece_b.id}/transition", headers=headers, json={"action": "approve"})
    assert approve.status_code == 403
    bulk = api.post("/api/content/bulk-transition", headers=headers, json={"ids": [piece_b.id], "action": "approve"})
    assert bulk.json()["done"] == []
    assert bulk.json()["errors"][0]["status_code"] == 403


def test_client_cannot_read_or_edit_another_clients_leads(api, two_clients):
    _, user_a = two_clients["a"]
    client_b, _ = two_clients["b"]
    lead_b = two_clients["lead_b"]
    headers = auth(user_a)

    assert api.get(f"/api/leads?client_id={client_b.id}", headers=headers).status_code == 403
    assert api.get(f"/api/leads/pipeline?client_id={client_b.id}", headers=headers).status_code == 403
    assert api.patch(f"/api/leads/{lead_b.id}", headers=headers, json={"notes": "mine now"}).status_code == 403


def test_list_endpoints_are_pinned_to_own_client(api, two_clients, make_content):
    client_a, user_a = two_clients["a"]
    make_content(client_a, status="approved")
    headers = auth(user_a)

    content = api.get("/api/content", headers=headers).json()
    clients = api.get("/api/clients", headers=headers).json()
    leads = api.get("/api/leads", headers=headers).json()

    assert {item["client_id"] for item in content} == {client_a.id}
    assert [c["id"] for c in clients] == [client_a.id]
    assert leads == []


def test_client_cannot_call_team_only_routes(api, two_clients):
    client_a, user_a = two_clients["a"]
    headers = auth(user_a)

    assert api.get("/api/dashboard", headers=headers).status_code == 403
    assert api.post("/api/clients", headers=headers, json={"name": "X", "company": "Y"}).status_code == 403
    assert api.post(
        "/api/content", headers=headers, json={"client_id": client_a.id, "channel": "linkedin"}
    ).status_code == 403
    assert api.post("/api/ai/topics", headers=headers, json={"client_id": client_a.id}).status_code == 403
    assert api.post(f"/api/clients/{client_a.id}/onboarding", headers=headers, json={"step": "intake"}).status_code == 403


def test_clients_never_see_internal_drafts(api, two_clients, make_content):
    client_a, user_a = two_clients["a"]
    hidden = [make_content(client_a, status=s) for s in ("idea", "draft", "internal_review")]
    visible = make_content(client_a, status="client_review")
    headers = auth(user_a)

    listed = {item["id"] for item in api.get("/api/content", headers=headers).json()}

    assert visible.id in listed
    assert not listed & {piece.id for piece in hidden}
    for piece in hidden:
        assert api.get(f"/api/content/{piece.id}", headers=headers).status_code == 404


def test_client_may_only_edit_preference_fields(api, two_clients):
    client_a, user_a = two_clients["a"]
    headers = auth(user_a)

    allowed = api.patch(
        f"/api/clients/{client_a.id}", headers=headers, json={"brand_voice": "Warmer", "auto_approve_hours": 24}
    )
    blocked = api.patch(f"/api/clients/{client_a.id}", headers=headers, json={"status": "paused"})

    assert allowed.status_code == 200
    assert allowed.json()["auto_approve_hours"] == 24
    assert blocked.status_code == 403
