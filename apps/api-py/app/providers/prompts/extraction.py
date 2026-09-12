"""JSON-mode prompts for LLM-backed requirement/task extraction.

Used by OpenAI-compatible providers (Groq, Fireworks). Chunks are labeled
``[n]`` so the model can cite the exact chunk(s) a requirement/task came from;
the provider maps those labels back to chunk IDs.
"""
from __future__ import annotations

from app.providers.ai_provider import AIExtractRequirementsInput


def _render_chunks(chunks: list[dict[str, object]]) -> str:
    return "\n".join(
        f"[{i + 1}] {c.get('text', '')!s}" for i, c in enumerate(chunks)
    )


def build_extract_requirements_prompt(input: AIExtractRequirementsInput) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for structured requirement extraction."""
    system_prompt = (
        "You extract product requirements from project specification documents.\n"
        "Return ONLY valid JSON in this exact format:\n"
        '{"requirements": [{"title": "...", "description": "...", "chunkIndexes": [1, 3]}]}\n'
        "- title: a short, imperative heading (<= 10 words)\n"
        "- description: the full sentence(s) the requirement came from\n"
        "- chunkIndexes: the 1-based labels of the chunks that support this requirement\n"
        "Skip boilerplate, marketing text, and anything that is not an actionable requirement.\n"
        "Output the JSON object only — no markdown code fences, no explanation, no surrounding text."
    )

    user_prompt = (
        f"Source file: {input.sourceFilename}\n"
        "\n"
        "DOCUMENT CHUNKS (labeled [n]):\n"
        f"{_render_chunks(input.chunks)}"
    )

    return system_prompt, user_prompt
