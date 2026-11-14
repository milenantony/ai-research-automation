
import asyncio

import httpx
import pytest

from app.services.paper_retrieval.arxiv import (
    ArxivAPIError,
    ArxivClient,
)


SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom">

    <entry>
        <id>https://arxiv.org/abs/2401.12345</id>
        <title>  Artificial Intelligence Research  </title>
        <summary>
            This paper explores artificial intelligence applications.
        </summary>
        <published>2024-01-15T10:30:00Z</published>

        <author>
            <name>John Smith</name>
        </author>
        <author>
            <name>Jane Doe</name>
        </author>

        <link
            href="https://arxiv.org/pdf/2401.12345"
            title="pdf"
            type="application/pdf"
        />

        <arxiv:doi>10.1234/example</arxiv:doi>
    </entry>
</feed>
"""


def create_mock_client(handler):
    transport = httpx.MockTransport(handler)
    return ArxivClient(transport=transport)


def test_search_returns_parsed_papers():
    def handler(request):
        assert request.url.params["max_results"] == "10"
        assert request.url.params["sortBy"] == "relevance"

        return httpx.Response(
            200,
            text=SAMPLE_XML,
        )

    client = create_mock_client(handler)

    papers = asyncio.run(
        client.search("Artificial Intelligence")
    )

    assert len(papers) == 1

    paper = papers[0]

    assert paper.external_id == "2401.12345"
    assert paper.title == "Artificial Intelligence Research"
    assert "artificial intelligence" in paper.abstract.lower()
    assert paper.authors == ["John Smith", "Jane Doe"]
    assert paper.paper_url == "https://arxiv.org/abs/2401.12345"
    assert paper.pdf_url == "https://arxiv.org/pdf/2401.12345"
    assert paper.doi == "10.1234/example"
    assert paper.source == "arxiv"


def test_search_handles_missing_optional_metadata():
    xml = """<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
        <entry>
            <id>https://arxiv.org/abs/2401.12346</id>
            <title>Sample Research Paper</title>
            <summary>Sample abstract.</summary>
            <published>2024-02-10T12:00:00Z</published>
            <author>
                <name>John Smith</name>
            </author>
        </entry>
    </feed>
    """

    def handler(request):
        return httpx.Response(200, text=xml)

    client = create_mock_client(handler)

    papers = asyncio.run(
        client.search("Sample Research")
    )

    assert len(papers) == 1
    assert papers[0].pdf_url is None
    assert papers[0].doi is None


def test_search_returns_empty_list_when_no_papers_found():
    xml = """<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
    </feed>
    """

    def handler(request):
        return httpx.Response(200, text=xml)

    client = create_mock_client(handler)

    papers = asyncio.run(
        client.search("Nonexistent research topic")
    )

    assert papers == []


def test_search_rejects_empty_topic():
    client = ArxivClient()

    with pytest.raises(ValueError, match="cannot be empty"):
        asyncio.run(client.search("   "))


@pytest.mark.parametrize("max_results", [0, 101, -1])
def test_search_rejects_invalid_max_results(max_results):
    client = ArxivClient()

    with pytest.raises(ValueError, match="max_results"):
        asyncio.run(
            client.search("Machine Learning", max_results=max_results)
        )


def test_search_rejects_negative_start():
    client = ArxivClient()

    with pytest.raises(ValueError, match="start"):
        asyncio.run(
            client.search("Machine Learning", start=-1)
        )


def test_search_handles_http_errors():
    def handler(request):
        return httpx.Response(500)

    client = create_mock_client(handler)

    with pytest.raises(ArxivAPIError, match="Failed to retrieve"):
        asyncio.run(
            client.search("Machine Learning")
        )


def test_search_handles_invalid_xml():
    def handler(request):
        return httpx.Response(
            200,
            text="<invalid><xml>",
        )

    client = create_mock_client(handler)

    with pytest.raises(ArxivAPIError, match="Invalid response"):
        asyncio.run(
            client.search("Machine Learning")
        )
