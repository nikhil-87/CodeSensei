# Vector Store (ChromaDB)

The vector database powers RAG retrieval. Implemented by `ChromaVectorStore` in
`analysis-engine/engine/ai/vector_store.py`.

## Deployment

Runs as a container (`chromadb/chroma:0.5.5`) in the compose files:
- **Port:** 8000 (the image always binds 8000 internally; the client uses `CHROMA_PORT=8000`).
- **Persistence:** docker volume `chroma-data` → `/chroma/chroma`, `IS_PERSISTENT=TRUE`.
- **Telemetry:** `ANONYMIZED_TELEMETRY=FALSE`.
- **Health:** heartbeat endpoint `/api/v1/heartbeat`.

> Gotcha (learned the hard way): the Chroma image ignores `CHROMA_SERVER_HTTP_PORT` and
> always listens on 8000. Keep both the service and the client on 8000.

## Collections

One collection per repository:
```
collection = f"{CHROMA_COLLECTION_PREFIX}{repository_id}"   # e.g. repo_<uuid>
```
Per-repo collections keep working sets small (fast ANN) and make deletion trivial.

Distance metric: **cosine**.

## Operations

| Operation | Method | Notes |
| --- | --- | --- |
| Index/update | `upsert(ids, contents, metadatas, embeddings)` | Idempotent by `chunk_id` — safe to re-run |
| Retrieve | `query(embedding, top_k, filter)` → `StoredChunk[]` | Returns score + metadata (file/line/symbol) |
| Delete repo index | `delete_collection()` | Called on repository delete (privacy cleanup) |

## Why ChromaDB
- Free and self-hostable (no per-vector billing).
- Simple `upsert`/`query` API; persistent mode needs only a volume.
- Per-collection isolation matches the "per-repo index" model perfectly.

## Trade-offs / limitations
- Single-node; not horizontally sharded. Fine for the portfolio scale; a managed vector DB
  (pgvector, Pinecone, Qdrant) would be the path at larger scale.
- No built-in re-ranking; retrieval is pure cosine ANN plus tagged-file guarantees.
- Rebuilding an index = re-analyze the repo (chunks re-embed + upsert).

See [../decisions/0004-chromadb.md](../decisions/0004-chromadb.md) for alternatives
considered.
