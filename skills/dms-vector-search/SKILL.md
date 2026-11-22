---
name: dms-vector-search
description: Search demo and test documents in FLOWDOC/Paperless through the DMS MCP semantic pgvector index, summarize evidence, and link every used source. Use for questions about document contents, test plans, drawings, certificates, approvals, milestones, or delivery evidence. Do not use it to modify or approve documents.
---

# DMS Vector Search

Use the `DMS-Dokumente & Vektorsuche` MCP connection.

1. For meaning-based questions, call `search_dms_documents_semantic`. Use a short query containing the subject, project/order/article reference, and document kind when known.
2. If the index is empty or the user asks for newly added documents, call `refresh_dms_vector_index` once, then repeat the search. Stop and report the error if the refresh fails.
3. Use `get_dms_document` when a result needs authoritative metadata. Use the ordinary `search_dms_documents` tool for exact titles, identifiers, or serial numbers.
4. Summarize only statements supported by returned snippets or metadata. Distinguish a likely semantic match from a verified document fact.
5. Link every document used in the answer with its returned Paperless URL. Never invent a URL.

The index stores OCR chunks and deterministic 768-dimensional local embeddings in PostgreSQL/pgvector. It sends no document content to a cloud service. Document permissions remain authoritative in FLOWDOC; production use requires user-level identity and ACL filtering at the MCP boundary.
