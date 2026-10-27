import pytest
from pathlib import Path

from dotenv import load_dotenv

# Load test configuration before importing the application.
BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env.test", override=True)

from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.dependencies import get_db
from app.main import app
from app.models import ResearchJob


@pytest.fixture(scope="session", autouse=True)
def prepare_test_database():
    """Create the required tables in the test database."""
    Base.metadata.create_all(bind=engine)
    yield


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