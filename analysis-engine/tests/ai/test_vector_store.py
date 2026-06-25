"""Tests for :class:`engine.ai.ChromaVectorStore` using a stub Chroma client."""
from __future__ import annotations

from typing import Any

import pytest

from engine.ai.errors import VectorStoreError
from engine.ai.vector_store import ChromaVectorStore, ChromaVectorStoreOptions


class StubCollection:
    def __init__(self) -> None:
        self.upserts: list[dict[str, Any]] = []
        self.queries: list[dict[str, Any]] = []
        self._next_query_response: dict[str, Any] | None = None
        self._items: int = 0

    def upsert(self, **kwargs: Any) -> None:
        self.upserts.append(kwargs)
        self._items += len(kwargs.get("ids", []))

    def query(self, **kwargs: Any) -> dict[str, Any]:
        self.queries.append(kwargs)
        assert self._next_query_response is not None, "set _next_query_response first"
        return self._next_query_response

    def count(self) -> int:
        return self._items


class StubClient:
    def __init__(self) -> None:
        self.collections: dict[str, StubCollection] = {}

    def get_or_create_collection(self, name: str, **_: Any) -> StubCollection:
        return self.collections.setdefault(name, StubCollection())

    def delete_collection(self, name: str) -> None:
        self.collections.pop(name, None)


def _store(client: StubClient, repo_id: str = "abc") -> ChromaVectorStore:
    return ChromaVectorStore(
        ChromaVectorStoreOptions(repository_id=repo_id),
        client=client,
    )


def test_upsert_forwards_to_chroma_collection() -> None:
    client = StubClient()
    store = _store(client)
    store.upsert(
        ids=["c1"],
        contents=["snippet"],
        metadatas=[{"file_path": "a.py"}],
        embeddings=[[0.1, 0.2]],
    )
    coll = client.collections["repo_abc"]
    assert coll.upserts[0]["ids"] == ["c1"]
    assert coll.upserts[0]["documents"] == ["snippet"]
    assert coll.upserts[0]["metadatas"] == [{"file_path": "a.py"}]
    assert coll.upserts[0]["embeddings"] == [[0.1, 0.2]]


def test_upsert_validates_input_lengths() -> None:
    store = _store(StubClient())
    with pytest.raises(VectorStoreError):
        store.upsert(ids=["a"], contents=["x", "y"], metadatas=[{}], embeddings=[[0]])


def test_query_translates_distances_to_scores() -> None:
    client = StubClient()
    store = _store(client)
    coll = client.get_or_create_collection("repo_abc")
    coll._next_query_response = {
        "ids": [["c1", "c2"]],
        "documents": [["alpha", "beta"]],
        "metadatas": [[{"file_path": "a.py"}, {"file_path": "b.py"}]],
        "distances": [[0.1, 0.4]],  # cosine distance → score = 1 - d
    }

    hits = store.query([0.0, 1.0], top_k=2)
    assert [h.chunk_id for h in hits] == ["c1", "c2"]
    assert hits[0].score == pytest.approx(0.9)
    assert hits[1].score == pytest.approx(0.6)


def test_query_propagates_filter_to_chroma() -> None:
    client = StubClient()
    store = _store(client)
    coll = client.get_or_create_collection("repo_abc")
    coll._next_query_response = {
        "ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]],
    }
    store.query([0.0], top_k=3, filter={"file_path": "main.py"})
    assert coll.queries[0]["where"] == {"file_path": "main.py"}
    assert coll.queries[0]["n_results"] == 3


def test_count_returns_collection_count() -> None:
    client = StubClient()
    store = _store(client)
    store.upsert(
        ids=["c1", "c2"],
        contents=["x", "y"],
        metadatas=[{}, {}],
        embeddings=[[0.0], [0.0]],
    )
    assert store.count() == 2


def test_delete_collection_removes_it_from_client() -> None:
    client = StubClient()
    store = _store(client)
    store.upsert(
        ids=["c1"], contents=["x"], metadatas=[{}], embeddings=[[0.0]]
    )
    assert "repo_abc" in client.collections
    store.delete_collection()
    assert "repo_abc" not in client.collections


def test_upsert_with_no_ids_is_a_noop() -> None:
    client = StubClient()
    store = _store(client)
    store.upsert(ids=[], contents=[], metadatas=[], embeddings=[])
    assert client.collections == {}
