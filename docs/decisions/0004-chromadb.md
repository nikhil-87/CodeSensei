# ADR-0004: ChromaDB as the vector store

**Status:** Accepted

## Context
RAG needs approximate-nearest-neighbor search over code-chunk embeddings, isolated per
repository, on free infrastructure.

## Decision
Use **ChromaDB** (self-hosted container, persistent volume) with **one collection per
repository** (`repo_<repository_id>`), cosine distance, idempotent upsert by `chunk_id`.

## Alternatives considered
- **pgvector** — keeps everything in Postgres (one fewer service) but mixes a very
  different access pattern into the relational DB and needs an extension.
- **Pinecone / Qdrant Cloud** — great at scale but a paid/managed dependency.
- **FAISS (in-process)** — fast but no persistence/server model; awkward across worker + API.

## Consequences
- (+) Free, self-hostable, simple upsert/query API.
- (+) Per-repo collections keep working sets small and deletion trivial (drop collection).
- (+) Idempotent upsert → re-indexing is safe.
- (−) Single-node; not sharded — fine for portfolio scale, not web-scale.
- (−) The image quirk of always binding port 8000 caused a real misconfiguration bug
  (documented in [../ai/vector-store.md](../ai/vector-store.md)).

## Future
At larger scale, migrate to pgvector (consolidation) or a managed vector DB — abstracted
behind `ChromaVectorStore`, so it's a one-class change + re-index.
