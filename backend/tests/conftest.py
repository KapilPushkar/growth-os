"""Test fixtures: a throwaway SQLite database, no AI keys, and small factories.

Environment variables are set before any app import so settings, the engine
and the AI layer all pick them up.
"""

import os
import tempfile
from collections.abc import Callable, Iterator
from datetime import timedelta
from pathlib import Path

_TMP_DIR = tempfile.mkdtemp(prefix="growth-os-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_TMP_DIR, 'test.db').as_posix()}"
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""
os.environ["JWT_SECRET"] = "test-only-jwt-secret-that-is-long-enough"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.auth import create_access_token, hash_password  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import ONBOARDING_STEPS, Client, ContentPiece, User, utcnow  # noqa: E402

PASSWORD = "secret-pass"
# Hash once: PBKDF2 at 200k iterations is deliberately slow.
PASSWORD_HASH = hash_password(PASSWORD)


@pytest.fixture(autouse=True)
def _fresh_schema() -> Iterator[None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def api() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user)}"}


@pytest.fixture
def make_user(db: Session) -> Callable[..., User]:
    def factory(role: str = "admin", email: str | None = None, client_id: int | None = None) -> User:
        user = User(
            email=email or f"{role}{db.query(User).count() + 1}@test.dev",
            name=f"Test {role.title()}",
            role=role,
            client_id=client_id,
            password_hash=PASSWORD_HASH,
        )
        db.add(user)
        db.commit()
        return user

    return factory


@pytest.fixture
def make_client(db: Session, make_user) -> Callable[..., tuple[Client, User]]:
    """Create a live client with a client login."""

    def factory(name: str = "Asha Client", auto_approve_hours: int = 0) -> tuple[Client, User]:
        client = Client(
            name=name,
            title="Founder",
            company=f"{name.split()[0]} Co",
            industry="B2B SaaS",
            status="active",
            positioning="We make widgets simple.",
            brand_voice="Plain and practical.",
            tone_tags=["plain"],
            target_audience="Operations leaders at mid-size companies",
            content_pillars=["Operations excellence", "Founder lessons"],
            goals=["Grow pipeline"],
            channels=["linkedin", "x"],
            posting_cadence=2,
            auto_approve_hours=auto_approve_hours,
            onboarding={step: True for step in ONBOARDING_STEPS},
        )
        db.add(client)
        db.commit()
        login = make_user("client", email=f"{name.split()[0].lower()}@client.dev", client_id=client.id)
        return client, login

    return factory


@pytest.fixture
def make_content(db: Session) -> Callable[..., ContentPiece]:
    def factory(
        client: Client, status: str = "draft", hours_in_status: float = 0, **fields
    ) -> ContentPiece:
        piece = ContentPiece(
            client_id=client.id,
            title=fields.pop("title", f"Post in {status}"),
            channel=fields.pop("channel", "linkedin"),
            body=fields.pop("body", "Body text"),
            status=status,
            status_changed_at=utcnow() - timedelta(hours=hours_in_status),
            **fields,
        )
        db.add(piece)
        db.commit()
        return piece

    return factory
