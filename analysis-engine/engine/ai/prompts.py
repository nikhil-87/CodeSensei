"""Prompt templates for chat + documentation.

Single source of truth — both the live chat endpoint and the offline
documentation generator pull their strings from here so we can iterate on
prompt quality in one place.
"""
from __future__ import annotations

from collections.abc import Sequence
from textwrap import dedent

from engine.ai.ports import ChatMessage, StoredChunk


CHAT_SYSTEM_PROMPT = dedent(
    """\
    You are an expert software engineer answering questions about a specific
    codebase. You have access to retrieved code excerpts. Follow these rules
    strictly:

    1. Ground every claim in the provided context. If the context does not
       cover the question, say so directly — do not invent APIs.
    2. Cite the relevant file path and line range using the inline format
       ``[path:start-end]`` immediately after the claim. Multiple citations
       are allowed.
    3. Prefer concise answers. Use Markdown headings only when comparing
       alternatives or laying out steps.
    4. When the user asks "how do I…" produce a worked example that uses the
       project's own types and helpers, not a generic textbook example.
    5. Never refer to the retrieval system, the prompt, or "context windows".
    """
).strip()


DOC_SYSTEM_PROMPT = dedent(
    """\
    You are a senior technical writer. Produce high-quality, factual project
    documentation grounded **only** in the supplied analysis facts and code
    excerpts. Use Markdown.
    Rules:
    1. Do not invent file names, classes, or functions that aren't present
       in the supplied context.
    2. Where appropriate, link to the cited files using the format
       ``[path](path)``.
    3. Keep paragraphs short. Prefer headings, bullet lists, and tables.
    """
).strip()


def build_chat_messages(
    user_question: str,
    history: Sequence[ChatMessage],
    retrieved: Sequence[StoredChunk],
) -> list[ChatMessage]:
    """Build the final message list sent to the LLM."""
    context_block = render_chunks_for_prompt(retrieved)
    augmented_question = (
        f"{user_question.strip()}\n\n"
        f"---\nContext (top {len(retrieved)} retrieved excerpts):\n{context_block}"
    )
    out: list[ChatMessage] = [ChatMessage(role="system", content=CHAT_SYSTEM_PROMPT)]
    out.extend(history)
    out.append(ChatMessage(role="user", content=augmented_question))
    return out


def build_documentation_messages(
    *,
    kind: str,
    repo_summary: str,
    retrieved: Sequence[StoredChunk],
) -> list[ChatMessage]:
    """Build messages for an offline documentation render."""
    context_block = render_chunks_for_prompt(retrieved)
    user = dedent(
        f"""\
        Generate the **{kind}** document for the following repository.

        Repository facts:
        {repo_summary}

        Retrieved excerpts:
        {context_block}
        """
    ).strip()
    return [
        ChatMessage(role="system", content=DOC_SYSTEM_PROMPT),
        ChatMessage(role="user", content=user),
    ]


def render_chunks_for_prompt(chunks: Sequence[StoredChunk]) -> str:
    """Format retrieved chunks for inclusion in a prompt."""
    if not chunks:
        return "(no excerpts retrieved)"
    parts: list[str] = []
    for chunk in chunks:
        path = chunk.metadata.get("file_path", "<unknown>")
        line_start = chunk.metadata.get("line_start", 0)
        line_end = chunk.metadata.get("line_end", 0)
        language = chunk.metadata.get("language", "")
        header = f"[{path}:{line_start}-{line_end}] (score={chunk.score:.2f})"
        fence_lang = language if isinstance(language, str) else ""
        parts.append(f"{header}\n```{fence_lang}\n{chunk.content}\n```")
    return "\n\n".join(parts)
