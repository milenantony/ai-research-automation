import pytest
from pathlib import Path
from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from uuid import uuid4

from alembic import command
from alembic.config import Config
from dotenv import dotenv_values, load_dotenv

# Load test configuration before importing the application.
BACKEND_DIR = Path(__file__).resolve().parents[1]
TEST_ENV = BACKEND_DIR / ".env.test"
if not dotenv_values(TEST_ENV).get("DATABASE_URL"):
    raise RuntimeError("Set DATABASE_URL in backend/.env.test before running tests.")
load_dotenv(TEST_ENV, override=True)

from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import engine
from app.dependencies import get_db
from app.main import app
from app.models import Account, AccountSession
from app.services.account_security import SESSION_COOKIE, digest_token


@pytest.fixture(scope="session", autouse=True)
def prepare_test_database():
    """Apply Alembic migrations to the test database."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    command.upgrade(config, "head")


@pytest.fixture()
def db_session():
    """Give each test its own transaction."""
    connection = engine.connect()
    transaction = connection.begin()

    TestingSessionLocal = sessionmaker(
        bind=connection,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def anonymous_client(db_session):
    """Provide a test client connected to the isolated test session."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app, base_url="http://localhost") as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()

@pytest.fixture()
def client(anonymous_client, db_session):
    account = Account(email=f"{uuid4()}@example.com", password_hash="unused")
    db_session.add(account)
    db_session.flush()
    token = token_urlsafe(32)
    db_session.add(AccountSession(
        token_hash=digest_token(token), account_id=account.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    ))
    db_session.flush()
    anonymous_client.cookies.set(SESSION_COOKIE, token)
    return anonymous_client
