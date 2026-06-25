# Analysis Engine

Pure-Python code-analysis library used by the worker (Phase 5) to extract
structure, dependencies, complexity, and dead-code from cloned repositories.
The engine has **no web framework, no database, no async runtime** — it
takes a path on disk and returns plain dataclasses.

## Why a separate package?

* **Reusability** — the same engine powers the worker, the backend's read
  paths (via cached results), and a future CLI / batch tool.
* **Testability** — pure functions on dataclasses are trivial to fixture.
* **Boundaries** — Clean Architecture insists analysis logic doesn't know
  about HTTP, ORM, or queueing concerns.

## Public API

```python
from pathlib import Path
from engine import AnalysisOptions, AnalysisOrchestrator

orchestrator = AnalysisOrchestrator(
    AnalysisOptions(workspace_root=Path("/var/lib/codesensei/workspaces"))
)

# Cloning + analysis in one shot:
result = orchestrator.run("https://github.com/octocat/Hello-World")

# Or analyse an already-cloned directory:
result = orchestrator.run_on_path(Path("/var/lib/codesensei/workspaces/hello"))

print(result.file_count, result.total_lines)
for cycle in result.cycles:
    print("circular:", " -> ".join(cycle))
```

The returned [`RepositoryAnalysis`](engine/results.py) bundles everything
the worker persists: per-file analyses, dependency edges, cycles, dead-code
findings, language counts, and an architecture report (with Mermaid).

## Layout

```
analysis-engine/
├── engine/
│   ├── __init__.py                 # public re-exports
│   ├── orchestrator.py             # AnalysisOrchestrator + analyze()
│   ├── results.py                  # RepositoryAnalysis dataclasses
│   ├── ports.py                    # ProgressReporter Protocol
│   ├── exceptions.py               # CloneError, RepositoryTooLargeError, ...
│   ├── cloning/
│   │   └── git_cloner.py           # safe `git clone` with size cap & timeouts
│   ├── walker/
│   │   └── file_walker.py          # gitignore-aware, binary-skipping walker
│   ├── languages/
│   │   └── detector.py             # extension/filename → canonical name
│   ├── parsers/
│   │   ├── base.py                 # Parser Protocol + ParseInput / ParseOutput
│   │   ├── registry.py             # language → parser, with fallback
│   │   ├── python_parser.py        # high-fidelity stdlib `ast` parser
│   │   ├── tree_sitter_parser.py   # multi-language (optional dependency)
│   │   └── regex_parser.py         # always-available fallback (JS/TS/Java/Go/Rust/C/C++/C#)
│   ├── graph/
│   │   ├── builder.py              # imports → resolved file-level edges
│   │   ├── cycles.py               # iterative Tarjan SCC
│   │   └── traversal.py            # reverse BFS for impact analysis
│   ├── dead_code/
│   │   └── detector.py             # cross-file unused-symbol heuristics
│   ├── architecture/
│   │   └── classifier.py           # layer detection + violation report + Mermaid
│   └── ai/                         # Phase 4 — RAG sub-package
│       ├── __init__.py             # public re-exports
│       ├── ports.py                # VectorStore / EmbeddingFunction / GenerationFunction
│       ├── chunker.py              # symbol-aware code splitter
│       ├── ollama_client.py        # httpx client (chat + embed, streaming)
│       ├── vector_store.py         # ChromaDB-backed VectorStore
│       ├── prompts.py              # chat + documentation prompt templates
│       ├── rag_chain.py            # index_repository + stream_chat
│       ├── documentation_writer.py # LLM-augmented doc generator
│       └── errors.py               # AIError hierarchy
├── tests/                          # hermetic — no network, no git, no Ollama, no Chroma
│   ├── conftest.py                 # `make_repo` synthetic-repo factory
│   ├── test_python_parser.py
│   ├── test_regex_parser.py
│   ├── test_graph.py
│   ├── test_architecture.py
│   ├── test_orchestrator.py
│   └── ai/
│       ├── fakes.py                # FakeEmbedder / FakeVectorStore / FakeStreamGenerator
│       ├── test_chunker.py
│       ├── test_prompts.py
│       ├── test_rag_chain.py
│       ├── test_documentation_writer.py
│       ├── test_ollama_client.py   # uses httpx MockTransport
│       └── test_vector_store.py    # uses Chroma stub client
└── pyproject.toml
```

## Design rules

* **Parsers are Protocols, not subclasses.** Duck typing makes adding
  languages a one-file change.
* **Every parser MUST be defensive.** The registry wraps every call in
  `try`/`except`; a single broken file never fails a whole run.
* **Three resolution tiers** — native parser → tree-sitter (if installed)
  → regex fallback. Tree-sitter is optional so the engine ships in a slim
  Docker image when needed.
* **Dataclasses are frozen.** Results are immutable so callers can cache
  / hash them safely.
* **Deterministic output.** `parse_all` sorts files lexicographically; SCC
  detection preserves first-seen order. Identical input → identical output
  → diff-friendly snapshots in tests.

## Performance

* Parsing is parallelised via `ThreadPoolExecutor` (parsers are Python and
  release the GIL during regex / AST work; we picked threads over
  processes to avoid per-task pickling cost).
* The walker prunes vendor / build directories *before* `stat` calls.
* Per-file size cap (2 MB by default) + total file cap (5000) bound the
  worst case.

## What's deliberately not here

| Capability | Where it lives |
| --- | --- |
| Persisting results to Postgres | Worker (Phase 5) |
| Streaming progress over SSE | Backend (Phase 2) |
| LLM-augmented documentation | `engine.ai.LlmDocumentationWriter` (this package) |
| RAG / embeddings / chat | `engine.ai.RagChain` (this package) |
| Wiring `RagChain` into the SSE endpoint | Worker (Phase 5) |

## AI sub-package quick-tour

```python
from engine.ai import (
    OllamaClient, OllamaSettings,
    ChromaVectorStore, ChromaVectorStoreOptions,
    RagChain, ChatRequest,
)

ollama = OllamaClient(OllamaSettings(base_url="http://localhost:11434"))
store = ChromaVectorStore(ChromaVectorStoreOptions(host="localhost", port=8000, repository_id="abc"))

chain = RagChain(
    vector_store=store,
    embedding_fn=ollama.embed,
    generation_stream_fn=ollama.stream_chat,
)

# 1. Index — typically called by the worker after analysis completes.
chain.index_repository(result.files, sources={f.path: read(f.path) for f in result.files})

# 2. Query — typically called by the backend SSE endpoint.
for event in chain.stream_chat(ChatRequest(question="How is auth implemented?", top_k=8)):
    print(event.event, event.content or event.error or event.citations)
```

The chain yields events that map 1:1 onto the backend's
[`ChatTokenEvent`](../backend/app/schemas/ai.py) schema (`citations` →
`token`* → `done`, or a single `error`).

## Verification

```powershell
cd analysis-engine
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]

ruff check engine tests
mypy engine
pytest -q
```
