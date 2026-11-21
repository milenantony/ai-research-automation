from uuid import UUID

from app.models.research_gap_analysis import ResearchGapAnalysis
from app.models.research_paper import ResearchPaper
from app.models.research_summary import ResearchSummary


def build_report(
    topic: str,
    summary: ResearchSummary,
    summary_paper_ids: list[UUID],
    analysis: ResearchGapAnalysis,
    papers: list[ResearchPaper],
) -> str:
    approved = [
        gap for gap in analysis.gaps
        if gap.get("review_status") == "approved"
    ]
    if not approved:
        raise ValueError("Approve at least one gap before generating a report")
    selected_ids = set(analysis.selected_paper_ids)
    if any(
        paper_id not in selected_ids
        for gap in approved
        for paper_id in gap["supporting_paper_ids"]
    ):
        raise ValueError("An approved gap cites an unselected paper")

    papers_by_id = {paper.id: paper for paper in papers}
    source_ids = list(dict.fromkeys(
        summary_paper_ids + [
            UUID(paper_id)
            for gap in approved
            for paper_id in gap["supporting_paper_ids"]
        ]
    ))
    if any(paper_id not in papers_by_id for paper_id in source_ids):
        raise ValueError("A report source paper is unavailable")

    citation_numbers = {
        paper_id: number
        for number, paper_id in enumerate(source_ids, start=1)
    }

    lines = [
        f"# Research Report: {topic}",
        "",
        "## Research summary",
        "",
        summary.summary.strip(),
        "",
        "The summary was generated from the abstracts of these papers: "
        + ", ".join(
            f"[{citation_numbers[paper_id]}]"
            for paper_id in summary_paper_ids
        )
        + ".",
        "",
        "## Reviewed research gaps",
        "",
    ]

    for number, gap in enumerate(approved, start=1):
        citations = ", ".join(
            f"[{citation_numbers[UUID(paper_id)]}]"
            for paper_id in gap["supporting_paper_ids"]
        )
        lines.extend([
            f"### Gap {number}: {gap['description']}",
            "",
            f"Category: {gap['category']}.",
            "",
            f"Evidence from the supplied abstracts: {gap['evidence']} {citations}",
            "",
        ])

    lines.extend([
        "## References",
        "",
    ])
    for paper_id in source_ids:
        paper = papers_by_id[paper_id]
        reference = f"[{citation_numbers[paper_id]}] {paper.title}."
        if paper.doi:
            reference += f" DOI: {paper.doi}."
        elif paper.paper_url:
            reference += f" URL: {paper.paper_url}."
        lines.append(reference)

    lines.extend([
        "",
        "## Scope",
        "",
        "This report is based on paper abstracts. The gaps are reviewed "
        "proposals, not proof of absence in the wider literature.",
    ])
    return "\n".join(lines)