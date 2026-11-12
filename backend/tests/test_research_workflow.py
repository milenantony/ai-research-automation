
import pytest
from unittest.mock import Mock

from app.services.research_workflow import ResearchWorkflow


def test_generate_summary():
    mock_llm = Mock()
    mock_llm.generate.return_value = "AI research summary."

    workflow = ResearchWorkflow(llm_service=mock_llm)

    result = workflow.generate_summary(
        topic="Applications of RAG in healthcare",
        research_context="RAG improves access to relevant medical information.",
    )

    assert result == "AI research summary."
    mock_llm.generate.assert_called_once()

    prompt = mock_llm.generate.call_args[0][0]

    assert "Applications of RAG in healthcare" in prompt
    assert "RAG improves access to relevant medical information." in prompt


def test_generate_summary_with_empty_topic():
    mock_llm = Mock()
    workflow = ResearchWorkflow(llm_service=mock_llm)

    with pytest.raises(ValueError, match="Research topic cannot be empty"):
        workflow.generate_summary(
            topic=" ",
            research_context="Some research material",
        )

    mock_llm.generate.assert_not_called()


def test_generate_summary_with_empty_context():
    mock_llm = Mock()
    workflow = ResearchWorkflow(llm_service=mock_llm)

    with pytest.raises(ValueError, match="Research context cannot be empty"):
        workflow.generate_summary(
            topic="Applications of RAG in healthcare",
            research_context=" ",
        )

    mock_llm.generate.assert_not_called()
