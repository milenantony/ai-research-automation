import json
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.services.insight_extraction import extract_insights
from app.services.llm_exceptions import LLMProviderError
from app.services.passage_retrieval import RetrievedPassage


@pytest.mark.parametrize("citation", ["valid", "wrong-paper", "wrong-quote", "invalid-json"])
def test_insights_require_quotes_from_the_cited_passage(citation):
    passage = RetrievedPassage(
        job_id=uuid4(), paper_id=uuid4(), passage_text="Forecast error fell by 10%.",
        title="Forecasting", source="arxiv", external_id="1234", paper_url=None,
        doi=None, cosine_distance=0.0,
    )
    llm = Mock()
    llm.generate.return_value = json.dumps({"insights": [{
        "category": "finding",
        "claim": "Forecast error decreased.",
        "paper_id": str(uuid4() if citation == "wrong-paper" else passage.paper_id),
        "evidence_quote": "error increased" if citation == "wrong-quote" else "fell by 10%",
    }]})
    if citation == "invalid-json":
        llm.generate.return_value = "unstructured text"

    if citation != "valid":
        with pytest.raises(LLMProviderError):
            extract_insights("Forecast error", [passage], llm)
        return

    insight, = extract_insights("Forecast error", [passage], llm)
    assert insight.paper_id == passage.paper_id
    assert insight.evidence_quote == "fell by 10%"
    assert insight.external_id == passage.external_id


def test_no_passages_skips_generation():
    llm = Mock()
    assert extract_insights("Forecast error", [], llm) == []
    llm.generate.assert_not_called()
