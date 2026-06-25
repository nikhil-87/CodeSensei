# AI Documentation

How CodeSensei understands and answers questions about code.

| Doc | Covers |
| --- | --- |
| [rag-pipeline.md](rag-pipeline.md) | Indexing + querying, chunking, retrieval, prompting, citations, stateless vs session chat |
| [providers.md](providers.md) | LLM + embedding providers and how to switch them by config |
| [vector-store.md](vector-store.md) | ChromaDB deployment, per-repo collections, operations |

Source: `analysis-engine/engine/ai/` (chunker, embeddings, vector store, prompts, LLM
clients, `rag_chain.py`); backend `app/services/ai_service.py` + `chat_session_service.py`.
Security of the AI surface (prompt-injection, data isolation): see
[../security/threat-model.md](../security/threat-model.md).
