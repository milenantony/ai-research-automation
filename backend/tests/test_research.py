from unittest.mock import Mock
from sqlalchemy.exc import SQLAlchemyError
from app.services.llm_exceptions import (
    LLMConfigurationError,
    LLMProviderError,
)
from app.services.research_workflow import ResearchWorkflow




def test_create_research_job(client):
    response = client.post(
        "/research-jobs",
        json={
            "topic": "Applications of RAG in healthcare"
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["topic"] == "Applications of RAG in healthcare"
    assert data["status"] == "PENDING"
    assert "id" in data
    assert "created_at" in data


def test_get_research_job(client):
    create_response = client.post(
        "/research-jobs",
        json={
            "topic": "AI applications in medical research"
        },
    )

    assert create_response.status_code == 201

    job_id = create_response.json()["id"]

    response = client.get(f"/research-jobs/{job_id}")

    assert response.status_code == 200
    assert response.json()["id"] == job_id


def test_create_research_job_with_invalid_topic(client):
    response = client.post(
        "/research-jobs",
        json={
            "topic": "AI"
        },
    )

    assert response.status_code == 422


def test_get_nonexistent_research_job(client):
    response = client.get(
        "/research-jobs/00000000-0000-4000-8000-000000000000"
    )

    assert response.status_code == 404

def test_create_research_job_database_failure(client, db_session, monkeypatch):

    # Simulate database commit failure
    monkeypatch.setattr(
        db_session,
        "commit",
        Mock(side_effect=SQLAlchemyError("Database connection failed")),
    )

    # Track whether rollback is called
    rollback_mock = Mock(wraps=db_session.rollback)

    monkeypatch.setattr(
        db_session,
        "rollback",
        rollback_mock,
    )

    response = client.post(
        "/research-jobs",
        json={
            "topic": "AI applications in healthcare research"
        },
    )

    # Verify HTTP 500
    assert response.status_code == 500

    assert response.json()["detail"] == "Failed to create research job"

    # Verify transaction rollback
    rollback_mock.assert_called_once()

def test_get_research_job_database_failure(client, db_session, monkeypatch):

    # Simulate database query failure
    monkeypatch.setattr(
        db_session,
        "get",
        Mock(side_effect=SQLAlchemyError("Database connection failed")),
    )

    # Track rollback
    rollback_mock = Mock(wraps=db_session.rollback)

    monkeypatch.setattr(
        db_session,
        "rollback",
        rollback_mock,
    )

    response = client.get(
        "/research-jobs/00000000-0000-4000-8000-000000000000"
    )

    # Verify HTTP 500
    assert response.status_code == 500

    assert response.json()["detail"] == "Failed to retrieve research job"

    # Verify rollback
    rollback_mock.assert_called_once()

def test_update_research_job(client):
    create_response = client.post(
        "/research-jobs",
        json={
            "topic": "Applications of AI in healthcare"
        },
    )

    assert create_response.status_code == 201

    job_id = create_response.json()["id"]

    response = client.put(
        f"/research-jobs/{job_id}",
        json={
            "topic": "Applications of RAG in medical research"
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == job_id
    assert data["topic"] == "Applications of RAG in medical research"
    assert data["status"] == "PENDING"

    # Verify persistence through GET
    get_response = client.get(f"/research-jobs/{job_id}")

    assert get_response.status_code == 200
    assert get_response.json()["topic"] == "Applications of RAG in medical research"

def test_update_nonexistent_research_job(client):
    response = client.put(
        "/research-jobs/00000000-0000-4000-8000-000000000000",
        json={
            "topic": "Updated AI research topic"
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Research job not found"

def test_update_research_job_with_invalid_topic(client):
    create_response = client.post(
        "/research-jobs",
        json={
            "topic": "Valid AI research topic"
        },
    )

    job_id = create_response.json()["id"]

    response = client.put(
        f"/research-jobs/{job_id}",
        json={
            "topic": "AI"
        },
    )

    assert response.status_code == 422

def test_update_research_job_database_failure(
    client,
    db_session,
    monkeypatch,
):
    create_response = client.post(
        "/research-jobs",
        json={
            "topic": "Original AI research topic"
        },
    )

    job_id = create_response.json()["id"]

    # Simulate database commit failure
    monkeypatch.setattr(
        db_session,
        "commit",
        Mock(side_effect=SQLAlchemyError("Database connection failed")),
    )

    # Track rollback
    rollback_mock = Mock(wraps=db_session.rollback)

    monkeypatch.setattr(
        db_session,
        "rollback",
        rollback_mock,
    )

    response = client.put(
        f"/research-jobs/{job_id}",
        json={
            "topic": "Updated AI research topic"
        },
    )

    assert response.status_code == 500

    assert response.json()["detail"] == "Failed to update research job"

    rollback_mock.assert_called_once()

def test_delete_research_job(client):
    create_response = client.post(
        "/research-jobs",
        json={
            "topic": "AI applications in healthcare"
        },
    )

    job_id = create_response.json()["id"]

    response = client.delete(
        f"/research-jobs/{job_id}"
    )

    assert response.status_code == 204
    assert response.content == b""

    # Verify the record no longer exists
    get_response = client.get(
        f"/research-jobs/{job_id}"
    )

    assert get_response.status_code == 404

def test_delete_nonexistent_research_job(client):
    response = client.delete(
        "/research-jobs/00000000-0000-4000-8000-000000000000"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Research job not found"

def test_delete_research_job_database_failure(
    client,
    db_session,
    monkeypatch,
):
    create_response = client.post(
        "/research-jobs",
        json={
            "topic": "Original AI research topic"
        },
    )

    job_id = create_response.json()["id"]

    # Simulate database commit failure
    monkeypatch.setattr(
        db_session,
        "commit",
        Mock(side_effect=SQLAlchemyError("Database connection failed")),
    )

    # Track rollback
    rollback_mock = Mock(wraps=db_session.rollback)

    monkeypatch.setattr(
        db_session,
        "rollback",
        rollback_mock,
    )

    response = client.delete(
        f"/research-jobs/{job_id}"
    )

    assert response.status_code == 500

    assert response.json()["detail"] == "Failed to delete research job"

    rollback_mock.assert_called_once()

def test_get_research_jobs_default_pagination(client):
    response = client.get("/research-jobs")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_research_jobs_custom_pagination(client):
    response = client.get(
        "/research-jobs?skip=0&limit=5"
    )

    assert response.status_code == 200
    assert len(response.json()) <= 5


def test_get_research_jobs_invalid_skip(client):
    response = client.get(
        "/research-jobs?skip=-1"
    )

    assert response.status_code == 422

def test_get_research_jobs_invalid_limit(client):
    response = client.get(
        "/research-jobs?limit=101"
    )

    assert response.status_code == 422

def test_get_research_jobs_filter_by_status(client):
    client.post(
        "/research-jobs",
        json={"topic": "AI in healthcare"}
    )

    response = client.get(
        "/research-jobs?status=PENDING"
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)

    for job in response.json():
        assert job["status"] == "PENDING"


def test_get_research_jobs_filter_no_results(client):
    response = client.get(
        "/research-jobs?status=COMPLETED"
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_research_jobs_invalid_status(client):
    response = client.get(
        "/research-jobs?status=INVALID"
    )

    assert response.status_code == 422


def test_generate_summary_configuration_error(client, monkeypatch):
    create_response = client.post(
        "/research-jobs",
        json={"topic": "AI applications in healthcare research"},
    )

    job_id = create_response.json()["id"]

    monkeypatch.setattr(
        ResearchWorkflow,
        "__init__",
        lambda self: None,
    )

    monkeypatch.setattr(
        ResearchWorkflow,
        "generate_summary",
        Mock(side_effect=LLMConfigurationError("Missing API key")),
    )

    response = client.post(
        f"/research-jobs/{job_id}/generate-summary",
        json={"research_context": "Research findings about AI in healthcare."},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "LLM configuration error"


def test_generate_summary_provider_error(client, monkeypatch):
    create_response = client.post(
        "/research-jobs",
        json={"topic": "AI applications in healthcare research"},
    )

    job_id = create_response.json()["id"]

    monkeypatch.setattr(
        ResearchWorkflow,
        "__init__",
        lambda self: None,
    )

    monkeypatch.setattr(
        ResearchWorkflow,
        "generate_summary",
        Mock(side_effect=LLMProviderError("Gemini API unavailable")),
    )

    response = client.post(
        f"/research-jobs/{job_id}/generate-summary",
        json={"research_context": "Research findings about AI in healthcare."},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "LLM provider request failed"


def test_generate_summary_value_error(client, monkeypatch):
    create_response = client.post(
        "/research-jobs",
        json={"topic": "AI applications in healthcare research"},
    )

    job_id = create_response.json()["id"]

    monkeypatch.setattr(
        ResearchWorkflow,
        "__init__",
        lambda self: None,
    )

    monkeypatch.setattr(
        ResearchWorkflow,
        "generate_summary",
        Mock(side_effect=ValueError("Invalid research context")),
    )

    response = client.post(
        f"/research-jobs/{job_id}/generate-summary",
        json={"research_context": "Research findings about AI in healthcare."},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid research context"


def test_generate_summary_unexpected_error(client, monkeypatch):
    create_response = client.post(
        "/research-jobs",
        json={"topic": "AI applications in healthcare research"},
    )

    job_id = create_response.json()["id"]

    monkeypatch.setattr(
        ResearchWorkflow,
        "__init__",
        lambda self: None,
    )

    monkeypatch.setattr(
        ResearchWorkflow,
        "generate_summary",
        Mock(side_effect=Exception("Unexpected failure")),
    )

    response = client.post(
        f"/research-jobs/{job_id}/generate-summary",
        json={"research_context": "Research findings about AI in healthcare."},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Failed to generate research summary"
