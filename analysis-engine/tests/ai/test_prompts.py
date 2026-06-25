"""Tests for prompt building helpers."""
from __future__ import annotations

from engine.ai.ports import ChatMessage, StoredChunk
from engine.ai.prompts import (
    CHAT_SYSTEM_PROMPT,
    DOC_SYSTEM_PROMPT,
    build_chat_messages,
    build_documentation_messages,
    render_chunks_for_prompt,
)


def _chunk(path: str, start: int, end: int, content: str, score: float = 0.9) -> StoredChunk:
    return StoredChunk(
        chunk_id=f"{path}::{start}-{end}",
        content=content,
        metadata={
            "file_path": path,
            "line_start": start,
            "line_end": end,
            "language": "python",
        },
        score=score,
    )


def test_render_chunks_includes_path_lines_and_score() -> None:
    rendered = render_chunks_for_prompt(
        [_chunk("src/app.py", 10, 20, "def hi(): ...", score=0.83)]
    )
    assert "[src/app.py:10-20]" in rendered
    assert "score=0.83" in rendered
    assert "```python" in rendered
    assert "def hi(): ..." in rendered


def test_render_chunks_with_no_input_returns_placeholder() -> None:
    assert render_chunks_for_prompt([]) == "(no excerpts retrieved)"


def test_build_chat_messages_layout_is_system_history_user() -> None:
    history = (
        ChatMessage(role="user", content="earlier"),
        ChatMessage(role="assistant", content="reply"),
    )
    messages = build_chat_messages(
        user_question="What does X do?",
        history=history,
        retrieved=[_chunk("a.py", 1, 5, "x = 1")],
    )

    assert messages[0].role == "system"
    assert messages[0].content == CHAT_SYSTEM_PROMPT
    assert messages[1:3] == list(history)
    assert messages[-1].role == "user"
    assert "What does X do?" in messages[-1].content
    assert "[a.py:1-5]" in messages[-1].content


def test_build_documentation_messages_uses_doc_system_prompt() -> None:
    messages = build_documentation_messages(
        kind="readme",
        repo_summary="42 Python files",
        retrieved=[_chunk("main.py", 1, 3, "print('hello')")],
    )
    assert messages[0].content == DOC_SYSTEM_PROMPT
    assert messages[-1].role == "user"
    assert "**readme**" in messages[-1].content
    assert "42 Python files" in messages[-1].content
    assert "[main.py:1-3]" in messages[-1].content
