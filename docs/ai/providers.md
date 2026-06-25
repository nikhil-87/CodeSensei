# AI Providers & Switching

AI is **provider-agnostic by configuration**. Two independent choices are made via env
vars; no code changes are needed to switch.

| Choice | Variable | Options | Default |
| --- | --- | --- | --- |
| Chat LLM | `LLM_PROVIDER` | `ollama` (local), `groq` (cloud) | `ollama` |
| Embeddings | `EMBEDDING_PROVIDER` | `ollama` (local), `huggingface` (cloud), `local` (CPU sentence-transformers) | `ollama` |

Type metadata for providers lives in `shared/config/providers.py`; clients live in
`analysis-engine/engine/ai/`.

## LLM providers

### Groq (recommended for free-tier cloud)
- Client: `engine/ai/groq_client.py`; API: `https://api.groq.com/openai/v1` (OpenAI-compatible).
- Default model: **`llama-3.3-70b-versatile`** (`GROQ_CHAT_MODEL`). Alternatives:
  `llama-3.1-8b-instant`, `mixtral-8x7b-32768`.
- Requires `GROQ_API_KEY` (from console.groq.com — no credit card).
- Free-tier limit ≈ 30 requests/min. Streams token-by-token.

> Note: model names get deprecated. A prior decommission of `llama-3.1-70b-versatile` was
> resolved by switching to `llama-3.3-70b-versatile`. If chat 400s with a model error,
> update `GROQ_CHAT_MODEL`.

### Ollama (local / private)
- Client: `engine/ai/ollama_client.py`; endpoint `OLLAMA_BASE_URL` (default
  `http://ollama:11434` in docker, `http://localhost:11434` locally).
- Chat model `OLLAMA_CHAT_MODEL` (e.g. `deepseek-coder:6.7b` / `neural-chat`).
- No API key, no rate limit, but needs RAM/GPU — used in the full (non-free-tier) compose.

## Embedding providers

### HuggingFace (free-tier cloud)
- Client: `engine/ai/free_embeddings.py`; uses the router endpoint
  `https://router.huggingface.co`.
- Model `HUGGINGFACE_EMBED_MODEL` = `sentence-transformers/all-MiniLM-L6-v2` (384-dim).
- Requires `HUGGINGFACE_API_KEY` (from huggingface.co/settings/tokens).

### Ollama embeddings (local)
- Model `OLLAMA_EMBED_MODEL` = `nomic-embed-text`.

### Local sentence-transformers (CPU, no network)
- `EMBEDDING_PROVIDER=local`, `LOCAL_EMBED_MODEL=all-MiniLM-L6-v2`. Heaviest cold-start but
  zero external calls.

## How switching works (no code changes)

1. The worker's `build_runtime()` (`worker/app/ai_runtime.py`) reads `LLM_PROVIDER` /
   `EMBEDDING_PROVIDER` and constructs the matching clients into an `AIRuntime`.
2. The backend's `AIService` does the same at chat time.
3. The chosen embedding model is **stamped** onto the repo (`embedding_model =
   "provider:model"`). If you change embedding providers, **re-analyze** affected repos so
   their vectors match the query-time model (mismatched dimensions/space ⇒ poor retrieval).

## Switching matrix

| From → To | Steps | Re-index needed? |
| --- | --- | --- |
| Ollama LLM → Groq | set `LLM_PROVIDER=groq` + `GROQ_API_KEY`; restart backend+worker | No (LLM only) |
| Groq → Ollama | run Ollama, set `LLM_PROVIDER=ollama` + model; restart | No |
| HuggingFace emb → local | set `EMBEDDING_PROVIDER=local` + `LOCAL_EMBED_MODEL`; restart | **Yes** — re-analyze repos |
| Ollama emb → HuggingFace | set `EMBEDDING_PROVIDER=huggingface` + key; restart | **Yes** — re-analyze repos |

## Alternative providers (drop-in candidates)
- **LLM:** OpenAI / Anthropic — both have OpenAI-compatible or simple SDKs; would need a
  small client in `engine/ai/` mirroring `groq_client.py`, then a `LLM_PROVIDER` value.
- **Embeddings:** OpenAI `text-embedding-3-small`, Cohere — same pattern.

The clean client interface in `engine/ai/` is what keeps these additions to ~one file plus
an enum value. See [../decisions/0009-provider-strategy.md](../decisions/0009-provider-strategy.md).
