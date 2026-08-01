"""Chat prompt builder.

Port of ``apps/api/src/prompts/chat.ts``. Kept separate from business logic.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.providers.ai_provider import AIChatInput


def build_chat_messages(input: AIChatInput) -> list[dict[str, str]]:
    ctx = "\n\n".join(
        f"[{i + 1}] ({p.filename}) {p.text}" for i, p in enumerate(input.passages[:8])
    )
    system = "\n".join([
        "You are Cartana, a project specification copilot.",
        "Answer using ONLY the passages below. If the answer is not in the passages, say so.",
        "Cite passages inline as [n] and refer to filenames when relevant. Be concise.",
        "",
        "--- PASSAGES ---",
        ctx,
    ])

    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    for m in input.history:
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": input.question})
    return messages
