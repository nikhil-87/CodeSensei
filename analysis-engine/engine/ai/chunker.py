"""Symbol-aware code chunker.

Why not naive line-based chunking? RAG quality on code drops sharply when
chunk boundaries fall in the middle of a function or class — the embedding
ends up averaging unrelated context. We use the symbols already extracted
by the analysis engine's parsers to align chunk boundaries with semantic
units (functions, classes, methods). Files with no detected symbols fall
back to overlapping line windows.
"""
from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from engine.results import FileAnalysis, Symbol


@dataclass(frozen=True, slots=True)
class CodeChunk:
    """A retrievable slice of source code."""

    chunk_id: str  # stable across runs (hash of file path + line range)
    file_path: str
    language: str | None
    line_start: int
    line_end: int
    content: str
    symbol_name: str | None  # primary symbol the chunk represents
    symbol_kind: str | None


@dataclass(frozen=True)
class ChunkOptions:
    """Tunable knobs for the chunker."""

    target_lines: int = 60
    max_lines: int = 200
    overlap_lines: int = 6
    min_chunk_chars: int = 40  # drop tiny chunks (license headers, etc.)


class CodeChunker:
    """Produces :class:`CodeChunk` instances aligned with parser symbols."""

    def __init__(self, options: ChunkOptions | None = None) -> None:
        self._options = options or ChunkOptions()

    def chunk_repository(
        self,
        files: Iterable[FileAnalysis],
        sources: dict[str, str],
    ) -> list[CodeChunk]:
        """Chunk every file that has a corresponding source string.

        ``sources`` is keyed by ``FileAnalysis.path``. Files without a
        source entry are silently skipped (e.g. binary files, files we
        couldn't decode).
        """
        chunks: list[CodeChunk] = []
        for file in files:
            source = sources.get(file.path)
            if source is None or not source.strip():
                continue
            chunks.extend(self.chunk_file(file, source))
        return chunks

    def chunk_file(self, file: FileAnalysis, source: str) -> list[CodeChunk]:
        """Chunk a single file into one or more :class:`CodeChunk` slices."""
        lines = source.splitlines()
        if not lines:
            return []

        ranges: list[tuple[int, int, Symbol | None]] = list(
            self._symbol_ranges(file.symbols, total_lines=len(lines))
        )
        if not ranges:
            ranges = list(self._sliding_windows(total_lines=len(lines)))

        chunks: list[CodeChunk] = []
        seen_ids: set[str] = set()
        for start, end, symbol in ranges:
            content = "\n".join(lines[start - 1 : end])
            if len(content) < self._options.min_chunk_chars:
                continue
            chunk_id = self._chunk_id(file.path, start, end)
            if chunk_id in seen_ids:
                continue
            seen_ids.add(chunk_id)
            chunks.append(
                CodeChunk(
                    chunk_id=chunk_id,
                    file_path=file.path,
                    language=file.language,
                    line_start=start,
                    line_end=end,
                    content=content,
                    symbol_name=symbol.name if symbol else None,
                    symbol_kind=symbol.kind if symbol else None,
                )
            )
        return chunks

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    def _symbol_ranges(
        self,
        symbols: tuple[Symbol, ...],
        *,
        total_lines: int,
    ) -> Iterator[tuple[int, int, Symbol | None]]:
        """Yield ``(start, end, symbol)`` ranges based on parser symbols.

        We only use top-level symbols (qualified names without dots) to
        avoid double-emitting class methods. Methods are absorbed into the
        enclosing class's range.
        """
        if not symbols:
            return
        top_level = [
            s for s in symbols if not (s.qualified_name and "." in s.qualified_name)
        ]
        if not top_level:
            return
        # Sort + de-duplicate overlapping ranges.
        ordered = sorted(top_level, key=lambda s: (s.line_start, -s.line_end))
        prev_end = 0
        for sym in ordered:
            start = max(1, min(sym.line_start, total_lines))
            end = max(start, min(sym.line_end or start, total_lines))
            # Cap the range to ``max_lines`` — large generated files / huge
            # classes would otherwise produce one giant chunk.
            if end - start + 1 > self._options.max_lines:
                end = start + self._options.max_lines - 1
            if end <= prev_end:
                continue
            start = max(start, prev_end + 1)
            prev_end = end
            yield start, end, sym

    def _sliding_windows(
        self, *, total_lines: int
    ) -> Iterator[tuple[int, int, Symbol | None]]:
        target = self._options.target_lines
        overlap = max(0, min(self._options.overlap_lines, target - 1))
        step = max(1, target - overlap)
        start = 1
        while start <= total_lines:
            end = min(start + target - 1, total_lines)
            yield start, end, None
            if end >= total_lines:
                break
            start += step

    @staticmethod
    def _chunk_id(file_path: str, start: int, end: int) -> str:
        return f"{file_path}::{start}-{end}"
