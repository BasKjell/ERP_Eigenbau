from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from typing import Any

from .config import Settings
from .paperless_client import PaperlessClient


class DmsVectorError(RuntimeError):
    """A sanitized vector-index error suitable for an MCP result."""


_DOMAIN_EXPANSIONS = {
    "abnahme": ("freigabe", "acceptance", "lieferung"),
    "arbeitsgang": ("operation", "fertigung", "montage"),
    "freigabe": ("genehmigung", "approval", "review"),
    "liefertermin": ("faelligkeit", "delivery", "meilenstein"),
    "montage": ("assembly", "fertigung", "arbeitsgang"),
    "pruefplan": ("pruefung", "qualitaet", "testplan"),
    "prüfplan": ("pruefung", "qualitaet", "testplan"),
    "seriennummer": ("serial", "rueckverfolgung", "traceability"),
    "stichprobe": ("sampling", "pruefung", "wareneingang"),
    "wareneingang": ("lieferung", "annahme", "incoming", "qualitaet"),
}

_MIN_RELEVANCE_SCORE = 0.1


def local_embedding(text: str, dimensions: int = 768) -> list[float]:
    """Create a deterministic local vector without sending text to a cloud service.

    Word, word-pair and character features make the demo useful for German
    manufacturing compounds. Domain expansions cover the core DMS vocabulary.
    """

    if dimensions != 768:
        raise DmsVectorError("DMS embedding dimensions must be 768")
    tokens = re.findall(r"[a-z0-9äöüß-]{2,}", text.casefold())
    expanded: list[str] = []
    for token in tokens:
        expanded.append(token)
        expanded.extend(_DOMAIN_EXPANSIONS.get(token, ()))
    features: list[tuple[str, float]] = [(f"w:{token}", 1.0) for token in expanded]
    features.extend(
        (f"b:{left}_{right}", 1.35)
        for left, right in zip(expanded, expanded[1:])
    )
    for token in expanded:
        compact = f"^{token}$"
        features.extend(
            (f"c:{compact[index:index + 3]}", 0.22)
            for index in range(max(0, len(compact) - 2))
        )
    vector = [0.0] * dimensions
    for feature, weight in features:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=16).digest()
        index = int.from_bytes(digest[:8], "big") % dimensions
        sign = 1.0 if digest[8] & 1 else -1.0
        vector[index] += sign * weight
    norm = math.sqrt(sum(value * value for value in vector))
    if not norm:
        raise DmsVectorError("query or document text is empty")
    return [value / norm for value in vector]


def chunk_document(text: str, max_chars: int = 1400, overlap: int = 180) -> list[str]:
    cleaned = re.sub(r"[ \t]+", " ", text).strip()
    if not cleaned:
        return []
    if max_chars < 200 or overlap < 0 or overlap >= max_chars:
        raise DmsVectorError("invalid chunk configuration")
    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + max_chars)
        if end < len(cleaned):
            boundary = max(cleaned.rfind("\n", start, end), cleaned.rfind(". ", start, end))
            if boundary > start + max_chars // 2:
                end = boundary + 1
        chunks.append(cleaned[start:end].strip())
        if end >= len(cleaned):
            break
        start = max(start + 1, end - overlap)
    return [chunk for chunk in chunks if chunk]


def _vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{value:.9f}" for value in vector) + "]"


class DmsVectorIndex:
    def __init__(
        self,
        settings: Settings,
        paperless: PaperlessClient,
        connection_factory: Callable[[], Any] | None = None,
    ) -> None:
        self.settings = settings
        self.paperless = paperless
        self._connection_factory = connection_factory

    def _connect(self) -> Any:
        if self._connection_factory is not None:
            return self._connection_factory()
        try:
            import psycopg

            return psycopg.connect(self.settings.knowledge_database_url, connect_timeout=5)
        except Exception as exc:  # pragma: no cover - driver/network boundary
            raise DmsVectorError("vector database is unavailable") from exc

    @staticmethod
    def _ensure_schema(connection: Any) -> None:
        with connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cursor.execute(
                """
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
                )
                """
            )
            for statement in (
                "ALTER TABLE knowledge_chunks ADD COLUMN IF NOT EXISTS chunk_index integer NOT NULL DEFAULT 0",
                "ALTER TABLE knowledge_chunks ADD COLUMN IF NOT EXISTS embedding_model text NOT NULL DEFAULT 'flow-hash-de-768-v1'",
                "ALTER TABLE knowledge_chunks ADD COLUMN IF NOT EXISTS content_hash text NOT NULL DEFAULT ''",
                "ALTER TABLE knowledge_chunks ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb",
                "ALTER TABLE knowledge_chunks ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now()",
            ):
                cursor.execute(statement)
            cursor.execute(
                """
                DELETE FROM knowledge_chunks older
                USING knowledge_chunks newer
                WHERE older.id < newer.id
                  AND older.source_system = newer.source_system
                  AND older.source_reference = newer.source_reference
                  AND older.chunk_index = newer.chunk_index
                """
            )
            cursor.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS knowledge_chunks_source_chunk_uq
                ON knowledge_chunks (source_system, source_reference, chunk_index)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS knowledge_chunks_embedding_hnsw
                ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)
                """
            )

    def refresh(self, max_documents: int = 100) -> dict[str, Any]:
        documents = self.paperless.list_documents_for_vector_index(max_documents)
        indexed_chunks = 0
        with self._connect() as connection:
            self._ensure_schema(connection)
            with connection.cursor() as cursor:
                # Rebuild the bounded demo collection so deleted Paperless
                # documents cannot remain searchable as stale index entries.
                cursor.execute(
                    "DELETE FROM knowledge_chunks WHERE source_system = %s",
                    ("Paperless-ngx",),
                )
                for document in documents:
                    document_id = int(document["id"])
                    reference = f"document:{document_id}"
                    title = str(document.get("title") or f"Dokument {document_id}")
                    content = str(document.get("content") or "")
                    chunks = chunk_document(f"{title}\n\n{content}")
                    metadata = {
                        key: document.get(key)
                        for key in (
                            "id",
                            "title",
                            "created",
                            "modified",
                            "document_type",
                            "correspondent",
                            "tags",
                            "original_file_name",
                            "url",
                        )
                    }
                    for chunk_index, content_chunk in enumerate(chunks):
                        embedding = local_embedding(
                            content_chunk, self.settings.dms_embedding_dimensions
                        )
                        cursor.execute(
                            """
                            INSERT INTO knowledge_chunks (
                                source_system, source_reference, content, embedding,
                                chunk_index, embedding_model, content_hash, metadata,
                                created_at, updated_at
                            ) VALUES (%s, %s, %s, %s::vector, %s, %s, %s, %s::jsonb, now(), now())
                            """,
                            (
                                "Paperless-ngx",
                                reference,
                                content_chunk,
                                _vector_literal(embedding),
                                chunk_index,
                                self.settings.dms_embedding_model,
                                hashlib.sha256(content_chunk.encode("utf-8")).hexdigest(),
                                json.dumps(metadata, ensure_ascii=False),
                            ),
                        )
                        indexed_chunks += 1
        return {
            "tool": "refresh_dms_vector_index",
            "status": "ok",
            "documents": len(documents),
            "chunks": indexed_chunks,
            "embedding_model": self.settings.dms_embedding_model,
            "indexed_at": datetime.now(UTC).isoformat(),
        }

    def status(self) -> dict[str, Any]:
        with self._connect() as connection:
            self._ensure_schema(connection)
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT count(DISTINCT source_reference), count(*), max(updated_at)
                    FROM knowledge_chunks WHERE source_system = %s
                    """,
                    ("Paperless-ngx",),
                )
                documents, chunks, updated_at = cursor.fetchone()
        return {
            "tool": "get_dms_vector_index_status",
            "status": "ok",
            "documents": documents,
            "chunks": chunks,
            "updated_at": updated_at.isoformat() if updated_at else None,
            "embedding_model": self.settings.dms_embedding_model,
            "database": "PostgreSQL/pgvector",
        }

    def search(self, query: str, max_results: int = 8) -> dict[str, Any]:
        selected_query = query.strip()
        if not selected_query:
            raise DmsVectorError("query is required")
        limit = max(1, min(int(max_results), 20))
        query_vector = _vector_literal(
            local_embedding(selected_query, self.settings.dms_embedding_dimensions)
        )
        with self._connect() as connection:
            self._ensure_schema(connection)
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT count(*) FROM knowledge_chunks WHERE source_system = %s",
                    ("Paperless-ngx",),
                )
                if int(cursor.fetchone()[0]) == 0:
                    return {
                        "tool": "search_dms_documents_semantic",
                        "status": "index_empty",
                        "query": selected_query,
                        "count": 0,
                        "documents": [],
                        "hint": "Run refresh_dms_vector_index before searching.",
                    }
                cursor.execute(
                    """
                    WITH distances AS (
                        SELECT source_reference, content, metadata,
                               embedding <=> %s::vector AS distance
                        FROM knowledge_chunks
                        WHERE source_system = %s AND embedding IS NOT NULL
                    ), ranked AS (
                        SELECT source_reference, content, metadata, distance,
                               row_number() OVER (
                                   PARTITION BY source_reference ORDER BY distance
                               ) AS chunk_rank
                        FROM distances
                    )
                    SELECT source_reference, content, metadata, 1 - distance AS score
                    FROM ranked
                    WHERE chunk_rank = 1
                    ORDER BY distance
                    LIMIT %s
                    """,
                    (query_vector, "Paperless-ngx", limit),
                )
                rows = cursor.fetchall()
        documents = []
        for reference, content, metadata, score in rows:
            numeric_score = float(score)
            if numeric_score < _MIN_RELEVANCE_SCORE:
                continue
            row_metadata = metadata if isinstance(metadata, dict) else json.loads(metadata)
            documents.append(
                {
                    **row_metadata,
                    "source_reference": reference,
                    "score": round(numeric_score, 4),
                    "snippet": str(content)[:700],
                }
            )
        return {
            "tool": "search_dms_documents_semantic",
            "status": "ok",
            "query": selected_query,
            "count": len(documents),
            "documents": documents,
            "minimum_relevance_score": _MIN_RELEVANCE_SCORE,
            "source": {
                "system": "PostgreSQL/pgvector",
                "collection": "Paperless-ngx",
            },
        }


def retry_refresh(
    index: DmsVectorIndex, wait_seconds: int = 90, max_documents: int = 100
) -> dict[str, Any]:
    import time

    deadline = time.monotonic() + max(0, wait_seconds)
    last_result: dict[str, Any] = {}
    while True:
        last_result = index.refresh(max_documents)
        if int(last_result.get("documents") or 0) > 0 or time.monotonic() >= deadline:
            return last_result
        time.sleep(3)


def iter_search_urls(result: dict[str, Any]) -> Iterator[str]:
    for document in result.get("documents", []):
        url = document.get("url")
        if url:
            yield str(url)
