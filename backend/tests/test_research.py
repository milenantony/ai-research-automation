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