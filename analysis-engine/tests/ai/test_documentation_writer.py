"""Tests for :class:`engine.ai.LlmDocumentationWriter`."""
from __future__ import annotations

from engine.ai.documentation_writer import LlmDocumentationWriter

from tests.ai.fakes import FakeEmbedder, FakeGenerator, FakeVectorStore


def test_generate_returns_doc_with_citations() -> None:
    embedder = FakeEmbedder()
    store = FakeVectorStore()
    # Seed two chunks; both should be returned (top_k = 12).
    for cid, path in [("c1", "src/main.py"), ("c2", "README.md")]:
        store.records[cid] = {
            "content": f"// {cid}",
            "metadata": {
                "file_path": path,
                "line_start": 1,
                "line_end": 5,
                "language": "python",
            },
            "embedding": embedder([f"seed {cid}"])[0],
        }

    generator = FakeGenerator("# Generated readme\n\nBody.")
    writer = LlmDocumentationWriter(
        vector_store=store,
        embedding_fn=embedder,
        generation_fn=generator,
        retrieval_top_k=12,
    )

    doc = writer.generate(kind="readme", repo_summary="A test project.")

    assert doc.kind == "readme"
    assert doc.body_markdown.startswith("# Generated readme")
    assert {c.chunk_id for c in doc.citations} == {"c1", "c2"}

    # The generator received the documentation system prompt.
    assert generator.last_messages is not None
    assert generator.last_messages[0].role == "system"
    assert "technical writer" in generator.last_messages[0].content


def test_supported_kinds_includes_all_canonical_doc_kinds() -> None:
    kinds = set(LlmDocumentationWriter.supported_kinds())
    assert {"readme", "architecture", "onboarding", "api", "technical_design", "summary"} <= kinds
