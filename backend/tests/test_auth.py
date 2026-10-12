from tests.conftest import PASSWORD, auth


def test_login_returns_token_and_user(api, make_user):
    user = make_user("admin", email="boss@test.dev")

    response = api.post("/api/auth/login", json={"email": "Boss@Test.dev ", "password": PASSWORD})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["id"] == user.id
    me = api.get("/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "boss@test.dev"


def test_wrong_password_is_401(api, make_user):
    make_user("admin", email="boss@test.dev")

    response = api.post("/api/auth/login", json={"email": "boss@test.dev", "password": "nope"})

    assert response.status_code == 401


def test_unknown_email_is_401_with_same_message(api, make_user):
    make_user("admin", email="boss@test.dev")

    wrong_password = api.post("/api/auth/login", json={"email": "boss@test.dev", "password": "x"})
    unknown_user = api.post("/api/auth/login", json={"email": "ghost@test.dev", "password": "x"})

    assert unknown_user.status_code == 401
    assert unknown_user.json() == wrong_password.json()


def test_inactive_user_cannot_log_in(api, db, make_user):
    user = make_user("strategist", email="gone@test.dev")
    user.is_active = False
    db.commit()

    response = api.post("/api/auth/login", json={"email": "gone@test.dev", "password": PASSWORD})

    assert response.status_code == 401


def test_unauthenticated_requests_are_401(api):
    for path in ("/api/auth/me", "/api/clients", "/api/content", "/api/dashboard", "/api/approvals"):
        assert api.get(path).status_code == 401, path


def test_invalid_token_is_401(api):
    response = api.get("/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"})

    assert response.status_code == 401


def test_users_list_is_team_only(api, make_user, make_client):
    admin = make_user("admin")
    _, client_user = make_client()

    assert api.get("/api/users", headers=auth(admin)).status_code == 200
    assert api.get("/api/users", headers=auth(client_user)).status_code == 403


def test_health_checks_the_database(api):
    assert api.get("/api/health").json() == {"status": "ok", "db": "ok"}
