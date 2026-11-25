from uuid import uuid4

from app.models.research_job import ResearchJob


def test_accounts_own_their_research_and_sessions(anonymous_client, db_session):
    client = anonymous_client
    first = {"email": " First@Example.com ", "password": "first secure passphrase"}
    second = {"email": "second@example.com", "password": "second secure passphrase"}

    assert client.get("/research-jobs").status_code == 401
    assert client.get("/auth/session").status_code == 401

    registered = client.post("/auth/register", json=first)
    assert registered.status_code == 201, registered.text
    assert registered.json()["email"] == "first@example.com"
    cookie = registered.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie
    first_token = client.cookies["paperx_session"]
    first_job = client.post("/research-jobs", json={"topic": "Private solar research"})
    assert first_job.status_code == 201, first_job.text
    path = f"/research-jobs/{first_job.json()['id']}"

    legacy = ResearchJob(topic="Existing unowned research")
    db_session.add(legacy)
    db_session.commit()
    assert client.get(f"/research-jobs/{legacy.id}").status_code == 404

    assert client.delete("/auth/session").status_code == 204
    client.cookies.set("paperx_session", first_token)
    assert client.get("/auth/session").status_code == 401
    client.cookies.clear()
    assert client.post("/auth/session", json={**first, "password": second["password"]}).status_code == 401
    assert client.post("/auth/register", json=first).status_code == 409
    assert client.post("/auth/register", json=second).status_code == 201
    assert client.get("/research-jobs").json() == []

    for method, suffix, payload in (
        ("GET", "", None),
        ("GET", "/papers", None),
        ("GET", "/summaries", None),
        ("GET", "/gap-analyses", None),
        ("GET", "/reports/latest", None),
        ("POST", "/papers:search", {"max_results": 1}),
        ("POST", "/papers:extract-insights", {"paper_ids": [str(uuid4())]}),
        ("POST", "/papers:analyze-gaps", {"paper_ids": [str(uuid4())]}),
        ("DELETE", "", None),
    ):
        response = client.request(method, f"{path}{suffix}", json=payload)
        assert response.status_code == 404, (method, suffix, response.text)

    assert client.post("/auth/session", json=first).status_code == 200
    assert [job["id"] for job in client.get("/research-jobs").json()] == [first_job.json()["id"]]
