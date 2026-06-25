# Phase 4 — AI Engine — Verification Guide

**Status:** ✅ Complete | **Tests:** 32 new (57 total) | **Run time:** ~0.6 s

This phase adds an `engine.ai` sub-package that turns the parsed
`RepositoryAnalysis` from Phase 3 into a queryable RAG index, and exposes
two public flows:

1. **Indexing** — `RagChain.index_repository(files, sources)` chunks every
   file along symbol boundaries, embeds chunks via Ollama, and persists
   them in a per-repository ChromaDB collection.
2. **Streaming chat** — `RagChain.stream_chat(ChatRequest)` retrieves the
   top-k chunks for a user question, formats a prompt with inline
   `[path:start-end]` citations, and streams tokens back as
   `ChatStreamEvent`s that match the backend's existing SSE schema.

A complementary `LlmDocumentationWriter` produces grounded Markdown
documents (`readme`, `architecture`, `onboarding`, `api`,
`technical_design`, `summary`) for the docs endpoint.

## Files created

```
analysis-engine/engine/ai/
├── __init__.py                  # re-exports the public surface
├── ports.py                     # VectorStore, EmbeddingFunction, GenerationStreamFunction, ChatStreamEvent, ChatMessage, StoredChunk, ChatCitationLite
├── errors.py                    # AIError → EmbeddingError | GenerationError | VectorStoreError
├── chunker.py                   # CodeChunker — symbol-aware splitter w/ sliding-window fallback
├── ollama_client.py             # OllamaClient — embed + chat + stream_chat (httpx, tenacity retry)
├── vector_store.py              # ChromaVectorStore — lazy chromadb import; cosine/L2/IP score normalisation
├── prompts.py                   # CHAT_SYSTEM_PROMPT, DOC_SYSTEM_PROMPT, build_chat_messages, build_documentation_messages
├── rag_chain.py                 # RagChain — index_repository, retrieve, stream_chat, hydrate_citations
└── documentation_writer.py      # LlmDocumentationWriter — kind → retrieval query → grounded doc

analysis-engine/tests/ai/
├── __init__.py
├── fakes.py                     # FakeEmbedder (sha256-based), FakeVectorStore (in-memory cosine), FakeStreamGenerator, FakeGenerator
├── test_chunker.py              # 6 cases — symbol-aligned + fallback + max_lines cap + min_chunk_chars
├── test_prompts.py              # 4 cases — citation markers, layout, doc system prompt
├── test_rag_chain.py            # 8 cases — index, skip, stream order, error event, retrieval ranking, embedder failures
├── test_documentation_writer.py # 2 cases — citations preserved, supported_kinds
├── test_ollama_client.py        # 5 cases — using httpx.MockTransport, no real network
└── test_vector_store.py         # 7 cases — using a stub Chroma client, no real container
```

## Design decisions worth knowing

### Symbol-aware chunking
Naive line chunking ruins RAG quality on code. The chunker reuses the
parser's symbol output: top-level functions / classes become single
chunks, methods are absorbed into their enclosing class, oversized
symbols are capped at `max_lines` (default 200), and files with no
detected symbols fall back to a sliding window with overlap. Every chunk
carries `(file_path, line_start, line_end, language, symbol_*)` so
citations are precise.

### Ports + fakes
`RagChain` knows nothing about Ollama or Chroma — it consumes three
callables (`EmbeddingFunction`, `GenerationStreamFunction`) and one
`VectorStore` Protocol. The tests inject deterministic in-memory fakes;
the worker (Phase 5) injects the real clients. This keeps unit tests
hermetic (no network, no Docker) and makes adding alternate backends
(OpenAI, Voyage, pgvector) a one-class change.

### Event taxonomy matches the backend exactly
`ChatStreamEvent.event` is `Literal["citations", "token", "done", "error"]`
— the same union used by the backend's `ChatTokenEvent` schema. The
backend SSE endpoint (currently stubbed at `app/api/v1/endpoints/ai.py`)
will be able to forward events without translation in Phase 5.

### Lazy `chromadb` import
`engine.ai.vector_store` imports `chromadb` only inside a method, so the
engine continues to import in environments where chromadb isn't
installed (CI image variants, dev machines doing pure parser work).
Tests use a stub client, so the test suite doesn't need chromadb either.

### Score normalisation
ChromaDB returns *distances* (smaller = closer); we convert to a 0..1
*similarity score* so the rest of the stack can rank/threshold without
caring whether the underlying space is cosine, L2, or IP.

## Execution flow

```
Indexing (Worker → engine.ai)
─────────────────────────────
RepositoryAnalysis.files ──► CodeChunker.chunk_repository
                                     │
                                     ▼
                              CodeChunk[ ] (id, path, lines, content, symbol)
                                     │
                                     ▼   batched (default 16)
                              EmbeddingFunction (Ollama: nomic-embed-text)
                                     │
                                     ▼
                              VectorStore.upsert (Chroma collection per repo_id)


Streaming chat (Backend → engine.ai)
────────────────────────────────────
ChatRequest ─► EmbeddingFunction(query)
                     │
                     ▼
              VectorStore.query(top_k)
                     │  StoredChunk[ ]   (with similarity score)
                     ▼
              build_chat_messages → [system + history + user-with-context]
                     │
                     ▼
              GenerationStreamFunction (Ollama: deepseek-coder:6.7b)
                     │
                     ▼
              ChatStreamEvent stream:
                  event=citations  (one)
                  event=token      (many)
                  event=done       (one)
              or event=error       (terminal, on any failure)
```

## Verification

### From the engine venv

```powershell
cd analysis-engine
.\.venv\Scripts\Activate.ps1
pip install -e .
pytest -q
```

Expected: **57 passed in <1s** — all hermetic, no network or Docker.

### Smoke-test the Ollama client (optional, requires running Ollama)

```powershell
ollama pull nomic-embed-text
ollama pull deepseek-coder:6.7b

python -c "from engine.ai import OllamaClient; c = OllamaClient(); print(len(c.embed(['hello'])[0]))"
python -c "from engine.ai import OllamaClient; from engine.ai.ports import ChatMessage; print(''.join(OllamaClient().stream_chat([ChatMessage(role='user', content='Say hi.')])))"
```

### Smoke-test the Chroma store (optional, requires running Chroma)

```powershell
docker run -d -p 8000:8000 chromadb/chroma:0.5.5
python -c "from engine.ai import ChromaVectorStore, ChromaVectorStoreOptions; s = ChromaVectorStore(ChromaVectorStoreOptions(host='localhost', port=8000, repository_id='smoke')); s.upsert(['c1'], ['hello'], [{'file_path': 'a.py', 'line_start': 1, 'line_end': 1}], [[0.1]*768]); print(s.count())"
```

## What's not here (per Clean-Architecture boundaries)

| Capability                                          | Where it will live      |
| --------------------------------------------------- | ----------------------- |
| Calling `RagChain` from the SSE chat endpoint       | Backend → Worker (P5)   |
| Triggering indexing as part of the analysis job    | Worker (P5)             |
| Re-indexing on pushed commits                       | Worker (P5)             |
| Surfacing AI citations to the frontend              | Frontend (P6)           |
| Production observability (token counts, latencies)  | Phase 9                 |
