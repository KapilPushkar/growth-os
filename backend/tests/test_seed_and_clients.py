from sqlalchemy import func, select

from app.models import CONTENT_STATUSES, LEAD_STAGES, Client, ContentPiece, Lead, MetricSnapshot, User
from app.seed import seed
from tests.conftest import PASSWORD, auth


def test_seed_creates_12_clients_and_3_team_users(db):
    summary = seed(db)

    assert summary == {"team": 3, "clients": 12}
    assert db.scalar(select(func.count(Client.id))) == 12
    assert db.scalar(select(func.count(User.id)).where(User.role.in_(("admin", "strategist")))) == 3
    assert db.scalar(select(func.count(User.id)).where(User.role == "client")) == 12
    assert db.scalar(select(func.count(Client.id)).where(Client.status == "active")) == 3


def test_seed_covers_every_status_and_stage_for_live_clients(db):
    seed(db)
    live = db.scalars(select(Client).where(Client.status == "active")).all()

    for client in live:
        statuses = set(db.scalars(select(ContentPiece.status).where(ContentPiece.client_id == client.id)))
        stages = set(db.scalars(select(Lead.stage).where(Lead.client_id == client.id)))
        weeks = db.scalar(select(func.count(MetricSnapshot.id)).where(MetricSnapshot.client_id == client.id))
        assert statuses == set(CONTENT_STATUSES), client.name
        assert stages == set(LEAD_STAGES), client.name
        assert weeks == 12


def test_seeded_logins_work(api, db):
    seed(db)

    for email, password in (("admin@growthos.dev", "admin123"), ("client1@growthos.dev", "client123")):
        response = api.post("/api/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200, email


def test_create_client_with_login_returns_temp_password_once(api, make_user):
    admin = make_user("admin")

    response = api.post(
        "/api/clients",
        headers=auth(admin),
        json={"name": "Nina New", "company": "NewCo", "email": "nina@newco.example", "channels": ["linkedin"]},
    )

    body = response.json()
    assert response.status_code == 201
    assert body["client"]["status"] == "onboarding"
    assert body["client"]["health"] is None
    login = api.post(
        "/api/auth/login", json={"email": "nina@newco.example", "password": body["login"]["temp_password"]}
    )
    assert login.status_code == 200
    assert login.json()["user"]["client_id"] == body["client"]["id"]
    again = api.get(f"/api/clients/{body['client']['id']}", headers=auth(admin)).json()
    assert "temp_password" not in str(again)


def test_duplicate_login_email_is_409(api, make_user):
    admin = make_user("admin", email="taken@test.dev")

    response = api.post(
        "/api/clients", headers=auth(admin), json={"name": "Dup", "company": "Dup Co", "email": "taken@test.dev"}
    )

    assert response.status_code == 409


def test_invalid_vocabulary_is_rejected(api, make_user):
    admin = make_user("admin")

    response = api.post(
        "/api/clients", headers=auth(admin), json={"name": "X", "company": "Y", "channels": ["tiktok"]}
    )

    assert response.status_code == 422


def test_completing_onboarding_takes_client_live(api, make_user):
    admin = make_user("admin")
    created = api.post(
        "/api/clients", headers=auth(admin), json={"name": "Olu Onboard", "company": "OnCo", "create_login": False}
    ).json()
    client_id = created["client"]["id"]

    for step in ("intake", "access", "strategy", "first_batch"):
        body = api.post(f"/api/clients/{client_id}/onboarding", headers=auth(admin), json={"step": step}).json()
        assert body["status"] == "onboarding"
    body = api.post(f"/api/clients/{client_id}/onboarding", headers=auth(admin), json={"step": "launch"}).json()

    assert body["status"] == "active"
    assert body["start_date"] is not None
    assert body["onboarding_pct"] == 100


def test_client_password_is_not_returned_by_login(api, make_client):
    _, client_user = make_client()

    body = api.post("/api/auth/login", json={"email": client_user.email, "password": PASSWORD}).json()

    assert "password" not in str(body["user"])
