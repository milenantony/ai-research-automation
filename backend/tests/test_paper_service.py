
from datetime import datetime, timezone

from sqlalchemy import select, func
import pytest
from sqlalchemy.exc import IntegrityError

from app.models.research_paper import ResearchPaper
from app.services.paper_retrieval.arxiv import ArxivPaper
from app.services.paper_service import PaperService
from app.services.paper_retrieval.semantic_scholar import SemanticScholarPaper


def make_arxiv_paper():
    return ArxivPaper(
        external_id="2501.00001",
        title="Machine Learning in Healthcare",
        abstract="A study of machine learning applications.",
        authors=["Alice", "Bob"],
        published_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        paper_url="https://arxiv.org/abs/2501.00001",
        pdf_url="https://arxiv.org/pdf/2501.00001",
        doi=None,
    )


def test_save_arxiv_paper(db_session):
    paper = make_arxiv_paper()

    saved = PaperService.save_papers(db_session, [paper])

    assert len(saved) == 1
    assert saved[0].external_id == paper.external_id
    assert saved[0].source == "arxiv"
    assert saved[0].title == paper.title
    assert saved[0].authors == ["Alice", "Bob"]

    count = db_session.scalar(
        select(func.count())
        .select_from(ResearchPaper)
    )

    assert count == 1


def test_duplicate_paper_not_inserted(db_session):
    paper = make_arxiv_paper()

    first = PaperService.save_papers(db_session, [paper])
    second = PaperService.save_papers(db_session, [paper])

    assert first[0].id == second[0].id

    count = db_session.scalar(
        select(func.count())
        .select_from(ResearchPaper)
    )

    assert count == 1

def test_save_multiple_papers(db_session):
    first_paper = make_arxiv_paper()

    second_paper = ArxivPaper(
        external_id="2501.00002",
        title="Deep Learning for Medical Imaging",
        abstract="Research on deep learning in medical imaging.",
        authors=["Charlie", "David"],
        published_date=datetime(2025, 1, 2, tzinfo=timezone.utc),
        paper_url="https://arxiv.org/abs/2501.00002",
        pdf_url="https://arxiv.org/pdf/2501.00002",
        doi=None,
    )

    saved = PaperService.save_papers(
        db_session,
        [first_paper, second_paper],
    )

    assert len(saved) == 2
    assert saved[0].external_id == "2501.00001"
    assert saved[1].external_id == "2501.00002"

    count = db_session.scalar(
        select(func.count()).select_from(ResearchPaper)
    )

    assert count == 2

def test_save_semantic_scholar_paper(db_session):
    paper = SemanticScholarPaper(
        external_id="semantic-test-001",
        title="Artificial Intelligence in Healthcare",
        abstract="A study of AI applications in healthcare.",
        authors=["Alice", "Charlie"],
        published_date=datetime(
            2025, 3, 15, tzinfo=timezone.utc
        ),
        paper_url="https://www.semanticscholar.org/paper/semantic-test-001",
        pdf_url=None,
        doi="10.1234/example",
    )

    saved = PaperService.save_papers(
        db_session,
        [paper],
    )

    assert len(saved) == 1
    assert saved[0].external_id == paper.external_id
    assert saved[0].source == "semantic_scholar"
    assert saved[0].title == paper.title
    assert saved[0].authors == ["Alice", "Charlie"]
    assert saved[0].doi == "10.1234/example"

    count = db_session.scalar(
        select(func.count()).select_from(ResearchPaper)
    )

    assert count == 1

def test_save_paper_database_failure(db_session):
    paper = make_arxiv_paper()
    paper.title = None

    with pytest.raises(IntegrityError):
        PaperService.save_papers(
            db_session,
            [paper],
        )

    db_session.rollback()

    valid_paper = make_arxiv_paper()

    saved = PaperService.save_papers(
        db_session,
        [valid_paper],
    )

    assert len(saved) == 1
    assert saved[0].title == valid_paper.title
