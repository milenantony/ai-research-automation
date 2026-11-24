import pytest
from pathlib import Path

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
from app.models import ResearchJob


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
def client(db_session):
    """Provide a test client connected to the isolated test session."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()