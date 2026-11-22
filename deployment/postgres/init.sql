CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id bigserial PRIMARY KEY,
    source_system text NOT NULL,
    source_reference text NOT NULL,
    content text NOT NULL,
    embedding vector(768),
    chunk_index integer NOT NULL DEFAULT 0,
    embedding_model text NOT NULL DEFAULT 'flow-hash-de-768-v1',
    content_hash text NOT NULL DEFAULT '',
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS knowledge_chunks_source_chunk_uq
    ON knowledge_chunks (source_system, source_reference, chunk_index);

CREATE INDEX IF NOT EXISTS knowledge_chunks_embedding_hnsw
    ON knowledge_chunks USING hnsw (embedding vector_cosine_ops);

COMMENT ON TABLE knowledge_chunks IS
    'Freigegebene, referenzierbare Wissensbausteine fuer die lokale DMS- und RAG-Suche.';
