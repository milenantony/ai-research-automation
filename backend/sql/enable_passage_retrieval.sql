-- Run after Alembic on a database with pgvector installed.
BEGIN;

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS research_abstract_passages (
    job_id uuid NOT NULL,
    paper_id uuid NOT NULL,
    embedding_model text NOT NULL,
    passage_text text NOT NULL,
    embedding vector(768) NOT NULL,
    PRIMARY KEY (job_id, paper_id, embedding_model),
    FOREIGN KEY (job_id, paper_id)
        REFERENCES research_job_papers (job_id, paper_id) ON DELETE CASCADE
);

COMMIT;
