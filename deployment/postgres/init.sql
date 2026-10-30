CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id bigserial PRIMARY KEY,
    source_system text NOT NULL,
    source_reference text NOT NULL,
    content text NOT NULL,
    embedding vector(768),
    created_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE knowledge_chunks IS
    'Freigegebene, referenzierbare Wissensbausteine fuer eine spaetere lokale RAG-Suche.';
