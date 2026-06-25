"""End-to-end RagChain tests using fakes for every external port."""
from __future__ import annotations

import pytest

from engine.ai.errors import EmbeddingError
from engine.ai.ports import ChatStreamEvent
from engine.ai.rag_chain import ChatRequest, RagChain, RagChainOptions
from engine.results import FileAnalysis, FileMetrics, Symbol

from tests.ai.fakes import FakeEmbedder, FakeStreamGenerator, FakeVectorStore


def _file(path: str, symbols: tuple[Symbol, ...]) -> FileAnalysis:
    return FileAnalysis(
        path=path,
        language="python",
        size_bytes=0,
        line_count=0,
        sha256="0" * 64,
        symbols=symbols,
        imports=(),
        metrics=FileMetrics(0, 0, 0, 0, 0),
        parser="python_ast",
    )


def _build_chain(stream_tokens: list[str] | None = None) -> tuple[RagChain, FakeEmbedder, FakeVectorStore, FakeStreamGenerator]:
    embedder = FakeEmbedder()
    store = FakeVectorStore()
    streamer = FakeStreamGenerator(stream_tokens or ["Hello", " world", "!"])
    chain = RagChain(
        vector_store=store,
        embedding_fn=embedder,
        generation_stream_fn=streamer,
        options=RagChainOptions(embedding_batch_size=4),
    )
    return chain, embedder, store, streamer


def test_index_repository_chunks_embeds_and_upserts() -> None:
    chain, embedder, store, _ = _build_chain()

    source = "\n".join(f"line {i}" for i in range(1, 41))
    file = _file(
        "src/svc.py",
        symbols=(
            Symbol("alpha", "function", 2, 8),
            Symbol("Beta", "class", 12, 30),
        ),
    )
    result = chain.index_repository([file], sources={"src/svc.py": source})

    assert result.files_indexed == 1
    assert result.files_skipped == 0
    assert result.chunks_indexed == 2
    assert store.count() == 2
    # Each upsert holds metadata for retrieval.
    sample = next(iter(store.records.values()))
    assert sample["metadata"]["file_path"] == "src/svc.py"
    assert sample["metadata"]["language"] == "python"
    # Embedder was called once per batch (here 1 batch since 2 < batch_size=4).
    assert len(embedder.calls) == 1


def test_index_repository_skips_files_without_source() -> None:
    chain, _, store, _ = _build_chain()

    file_a = _file("a.py", symbols=(Symbol("foo", "function", 1, 10),))
    file_b = _file("b.py", symbols=(Symbol("bar", "function", 1, 10),))

    long_source = "\n".join(f"line {i}" for i in range(1, 31))
    result = chain.index_repository(
        [file_a, file_b], sources={"a.py": long_source}  # b.py omitted
    )

    assert result.files_indexed == 1
    assert result.files_skipped == 1
    assert store.count() >= 1
    assert all(rec["metadata"]["file_path"] == "a.py" for rec in store.records.values())


def test_stream_chat_yields_citations_then_tokens_then_done() -> None:
    chain, _, store, streamer = _build_chain(stream_tokens=["Yes", ".", " Done"])

    # Seed the store with one chunk.
    store.records["chunk-1"] = {
        "content": "def hello(): pass",
        "metadata": {
            "file_path": "src/app.py",
            "line_start": 5,
            "line_end": 7,
            "language": "python",
        },
        "embedding": FakeEmbedder()(["def hello(): pass"])[0],
    }

    events = list(chain.stream_chat(ChatRequest(question="What does hello do?", top_k=3)))

    assert events[0].event == "citations"
    assert events[0].citations is not None
    assert events[0].citations[0].file_path == "src/app.py"

    token_events = [e for e in events if e.event == "token"]
    assert [e.content for e in token_events] == ["Yes", ".", " Done"]
    assert events[-1].event == "done"

    # The user message handed to the generator must contain the question
    # and the cited chunk.
    assert streamer.last_messages is not None
    user_msg = streamer.last_messages[-1]
    assert user_msg.role == "user"
    assert "What does hello do?" in user_msg.content
    assert "[src/app.py:5-7]" in user_msg.content


def test_stream_chat_emits_error_event_when_embedding_fails() -> None:
    class BrokenEmbedder:
        def __call__(self, texts):  # type: ignore[no-untyped-def]
            raise RuntimeError("Ollama unreachable")

    chain = RagChain(
        vector_store=FakeVectorStore(),
        embedding_fn=BrokenEmbedder(),
        generation_stream_fn=FakeStreamGenerator(["unused"]),
    )
    events = list(chain.stream_chat(ChatRequest(question="hi", top_k=1)))

    assert len(events) == 1
    assert events[0].event == "error"
    assert events[0].error is not None
    assert "Ollama unreachable" in events[0].error


def test_retrieve_orders_by_similarity() -> None:
    chain, embedder, store, _ = _build_chain()

    # Seed two chunks with predictable text.
    for cid, content in [("a", "alpha alpha alpha"), ("b", "beta gamma delta")]:
        store.records[cid] = {
            "content": content,
            "metadata": {"file_path": cid, "line_start": 1, "line_end": 1},
            "embedding": embedder([content])[0],
        }

    hits = chain.retrieve("alpha alpha alpha", top_k=2)
    assert hits[0].chunk_id == "a"
    assert hits[0].score >= hits[1].score


def test_retrieve_raises_when_embedder_returns_nothing() -> None:
    class EmptyEmbedder:
        def __call__(self, texts):  # type: ignore[no-untyped-def]
            return []

    chain = RagChain(
        vector_store=FakeVectorStore(),
        embedding_fn=EmptyEmbedder(),
        generation_stream_fn=FakeStreamGenerator([]),
    )
    with pytest.raises(EmbeddingError):
        chain.retrieve("anything")


def test_index_repository_raises_when_embedding_count_mismatches() -> None:
    class WrongCountEmbedder:
        def __call__(self, texts):  # type: ignore[no-untyped-def]
            return [[0.0] * 4]  # always 1 vector

    chain = RagChain(
        vector_store=FakeVectorStore(),
        embedding_fn=WrongCountEmbedder(),
        generation_stream_fn=FakeStreamGenerator([]),
    )
    file = _file("a.py", symbols=(Symbol("x", "function", 1, 10), Symbol("y", "function", 11, 20)))
    src = "\n".join(f"# meaningful padding line number {i:03d}" for i in range(1, 30))
    with pytest.raises(EmbeddingError):
        chain.index_repository([file], sources={"a.py": src})


def test_hydrate_citations_handles_missing_metadata() -> None:
    from engine.ai.ports import StoredChunk

    citations = RagChain.hydrate_citations(
        [
            StoredChunk(
                chunk_id="x",
                content="snippet",
                metadata={"file_path": "f.py", "line_start": 1, "line_end": 2},
                score=0.5,
            )
        ]
    )
    assert citations[0].file_path == "f.py"
    assert citations[0].language is None
    assert citations[0].symbol_name is None
