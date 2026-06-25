"""Tests for :class:`engine.ai.CodeChunker`."""
from __future__ import annotations

from engine.ai.chunker import ChunkOptions, CodeChunker
from engine.results import FileAnalysis, FileMetrics, Symbol


def _file(path: str, symbols: tuple[Symbol, ...] = ()) -> FileAnalysis:
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


def test_symbol_aware_chunking_aligns_with_top_level_symbols() -> None:
    source = "\n".join(f"line {i}" for i in range(1, 41))
    file = _file(
        "src/app.py",
        symbols=(
            Symbol("alpha", "function", 2, 8),
            Symbol("Beta", "class", 12, 30),
            Symbol("Beta.method", "method", 14, 18),  # nested — should be ignored
            Symbol("gamma", "function", 32, 38),
        ),
    )

    chunks = CodeChunker().chunk_file(file, source)

    line_ranges = [(c.line_start, c.line_end) for c in chunks]
    symbol_names = [c.symbol_name for c in chunks]
    assert line_ranges == [(2, 8), (12, 30), (32, 38)]
    assert symbol_names == ["alpha", "Beta", "gamma"]
    assert all(c.file_path == "src/app.py" for c in chunks)
    assert all(c.language == "python" for c in chunks)


def test_sliding_window_fallback_when_no_symbols() -> None:
    lines = [f"row {i}" for i in range(1, 51)]
    source = "\n".join(lines)
    file = _file("data/big.txt")

    chunks = CodeChunker(
        ChunkOptions(target_lines=20, overlap_lines=5, min_chunk_chars=1)
    ).chunk_file(file, source)

    assert len(chunks) >= 3
    # First chunk should start at line 1.
    assert chunks[0].line_start == 1
    # Final chunk should reach the end.
    assert chunks[-1].line_end == 50
    # Overlap: chunk[i+1].start should be < chunk[i].end + 1.
    for prev, nxt in zip(chunks[:-1], chunks[1:], strict=True):
        assert nxt.line_start < prev.line_end + 1


def test_chunk_id_is_stable_and_unique() -> None:
    source = "x = 1\ny = 2\nz = 3"
    file = _file("a.py")
    chunks_a = CodeChunker().chunk_file(file, source)
    chunks_b = CodeChunker().chunk_file(file, source)
    assert [c.chunk_id for c in chunks_a] == [c.chunk_id for c in chunks_b]
    assert len({c.chunk_id for c in chunks_a}) == len(chunks_a)


def test_tiny_files_dropped_by_min_chunk_chars() -> None:
    file = _file("license.txt")
    chunks = CodeChunker().chunk_file(file, "MIT")
    assert chunks == []


def test_chunk_repository_skips_files_without_source() -> None:
    files = [_file("a.py"), _file("b.py")]
    chunks = CodeChunker().chunk_repository(
        files,
        sources={"a.py": "print('hello')\n" * 20},
    )
    assert chunks  # only "a.py" produced chunks
    assert all(c.file_path == "a.py" for c in chunks)


def test_oversized_symbol_capped_to_max_lines() -> None:
    source = "\n".join(f"line {i}" for i in range(1, 1001))
    file = _file(
        "huge.py",
        symbols=(Symbol("massive", "function", 1, 1000),),
    )

    chunks = CodeChunker(
        ChunkOptions(target_lines=60, max_lines=200, overlap_lines=0)
    ).chunk_file(file, source)

    assert len(chunks) == 1
    assert chunks[0].line_end - chunks[0].line_start + 1 == 200
