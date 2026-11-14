
import asyncio

import httpx
import pytest

from app.services.paper_retrieval.semantic_scholar import (
    SemanticScholarAPIError,
    SemanticScholarClient,
)


SAMPLE_RESPONSE = {
    "total": 1,
    "offset": 0,
    "data": [
        {
            "paperId": "abc123",
            "title": "Artificial Intelligence Research",
            "abstract": "This paper explores AI applications.",
            "authors": [
                {"authorId": "1", "name": "John Smith"},
                {"authorId": "2", "name": "Jane Doe"},
            ],
            "publicationDate": "2024-01-15",
            "year": 2024,
            "externalIds": {
                "DOI": "10.1234/example",
                "ArXiv": "2401.12345",
            },
            "url": "https://www.semanticscholar.org/paper/abc123",
            "openAccessPdf": {
                "url": "https://example.com/paper.pdf",
                "status": "GREEN",
            },
        }
    ],
}


def create_mock_client(handler, api_key=None):
    transport = httpx.MockTransport(handler)

    return SemanticScholarClient(
        transport=transport,
        api_key=api_key,
    )


def test_search_returns_parsed_papers():
    def handler(request):
        assert request.url.params["query"] == "Artificial Intelligence"
        assert request.url.params["limit"] == "10"
        assert request.url.params["offset"] == "0"
        assert "paperId" in request.url.params["fields"]

        return httpx.Response(200, json=SAMPLE_RESPONSE)

    client = create_mock_client(handler)

    papers = asyncio.run(
        client.search("Artificial Intelligence")
    )

    assert len(papers) == 1

    paper = papers[0]

    assert paper.external_id == "abc123"
    assert paper.title == "Artificial Intelligence Research"
    assert paper.abstract == "This paper explores AI applications."
    assert paper.authors == ["John Smith", "Jane Doe"]
    assert paper.published_date.year == 2024
    assert paper.paper_url == (
        "https://www.semanticscholar.org/paper/abc123"
    )
    assert paper.pdf_url == "https://example.com/paper.pdf"
    assert paper.doi == "10.1234/example"
    assert paper.source == "semantic_scholar"


def test_search_sends_api_key_when_provided():
    def handler(request):
        assert request.headers["x-api-key"] == "test-api-key"

        return httpx.Response(200, json=SAMPLE_RESPONSE)

    client = create_mock_client(
        handler,
        api_key="test-api-key",
    )

    papers = asyncio.run(
        client.search("Machine Learning")
    )

    assert len(papers) == 1


def test_search_works_without_api_key():
    def handler(request):
        assert "x-api-key" not in request.headers

        return httpx.Response(200, json=SAMPLE_RESPONSE)

    client = create_mock_client(handler)

    papers = asyncio.run(
        client.search("Machine Learning")
    )

    assert len(papers) == 1


def test_search_handles_missing_optional_metadata():
    response_data = {
        "data": [
            {
                "paperId": "paper456",
                "title": "Sample Research Paper",
            }
        ]
    }

    def handler(request):
        return httpx.Response(200, json=response_data)

    client = create_mock_client(handler)

    papers = asyncio.run(
        client.search("Sample Research")
    )

    assert len(papers) == 1

    paper = papers[0]

    assert paper.abstract == ""
    assert paper.authors == []
    assert paper.published_date is None
    assert paper.pdf_url is None
    assert paper.doi is None


def test_search_uses_year_when_publication_date_is_missing():
    response_data = {
        "data": [
            {
                "paperId": "paper789",
                "title": "Year Based Research",
                "year": 2023,
            }
        ]
    }

    def handler(request):
        return httpx.Response(200, json=response_data)

    client = create_mock_client(handler)

    papers = asyncio.run(
        client.search("Research")
    )

    assert papers[0].published_date.year == 2023


def test_search_returns_empty_list_when_no_papers_found():
    def handler(request):
        return httpx.Response(
            200,
            json={"total": 0, "data": []},
        )

    client = create_mock_client(handler)

    papers = asyncio.run(
        client.search("Nonexistent research topic")
    )

    assert papers == []


def test_search_handles_invalid_paper_entries():
    response_data = {
        "data": [
            {"title": "Missing paper ID"},
            {"paperId": "paper123"},
            {
                "paperId": "paper456",
                "title": "Valid Paper",
            },
        ]
    }

    def handler(request):
        return httpx.Response(200, json=response_data)

    client = create_mock_client(handler)

    papers = asyncio.run(
        client.search("Research")
    )

    assert len(papers) == 1
    assert papers[0].external_id == "paper456"


def test_search_rejects_empty_topic():
    client = SemanticScholarClient()

    with pytest.raises(ValueError, match="cannot be empty"):
        asyncio.run(client.search("   "))


@pytest.mark.parametrize("max_results", [0, 101, -1])
def test_search_rejects_invalid_max_results(max_results):
    client = SemanticScholarClient()

    with pytest.raises(ValueError, match="max_results"):
        asyncio.run(
            client.search(
                "Machine Learning",
                max_results=max_results,
            )
        )


def test_search_rejects_negative_offset():
    client = SemanticScholarClient()

    with pytest.raises(ValueError, match="offset"):
        asyncio.run(
            client.search(
                "Machine Learning",
                offset=-1,
            )
        )


def test_search_supports_pagination():
    def handler(request):
        assert request.url.params["limit"] == "20"
        assert request.url.params["offset"] == "40"

        return httpx.Response(
            200,
            json={"total": 0, "data": []},
        )

    client = create_mock_client(handler)

    papers = asyncio.run(
        client.search(
            "Deep Learning",
            max_results=20,
            offset=40,
        )
    )

    assert papers == []


def test_search_handles_http_errors():
    def handler(request):
        return httpx.Response(500)

    client = create_mock_client(handler)

    with pytest.raises(
        SemanticScholarAPIError,
        match="Failed to retrieve",
    ):
        asyncio.run(
            client.search("Machine Learning")
        )


def test_search_handles_rate_limit():
    def handler(request):
        return httpx.Response(429)

    client = create_mock_client(handler)

    with pytest.raises(
        SemanticScholarAPIError,
        match="rate limit exceeded",
    ):
        asyncio.run(
            client.search("Machine Learning")
        )


def test_search_handles_connection_errors():
    def handler(request):
        raise httpx.ConnectError("Connection failed")

    client = create_mock_client(handler)

    with pytest.raises(
        SemanticScholarAPIError,
        match="Failed to connect",
    ):
        asyncio.run(
            client.search("Machine Learning")
        )


def test_search_handles_invalid_json():
    def handler(request):
        return httpx.Response(
            200,
            text="<invalid-json>",
        )

    client = create_mock_client(handler)

    with pytest.raises(
        SemanticScholarAPIError,
        match="Invalid response",
    ):
        asyncio.run(
            client.search("Machine Learning")
        )


def test_search_handles_invalid_response_structure():
    def handler(request):
        return httpx.Response(
            200,
            json={"data": "invalid"},
        )

    client = create_mock_client(handler)

    with pytest.raises(
        SemanticScholarAPIError,
        match="Invalid response",
    ):
        asyncio.run(
            client.search("Machine Learning")
        )
