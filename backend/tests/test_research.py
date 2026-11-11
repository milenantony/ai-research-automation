from unittest.mock import Mock
from sqlalchemy.exc import SQLAlchemyError




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
