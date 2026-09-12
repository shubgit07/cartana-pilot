"""Text chunking strategy.

Port of ``apps/api/src/modules/sources/chunking.ts``.

~700 chars per chunk with ~100 char overlap. Prefers paragraph > sentence >
word boundaries. Deliberately naive — smarter strategies can replace this
function without changing callers.
"""
from __future__ import annotations

from dataclasses import dataclass

CHUNK_SIZE = 700
CHUNK_OVERLAP = 100


@dataclass
class ChunkPiece:
    position: int
    text: str


@dataclass
class CodeChunkPiece:
    """One line-aligned code block with 1-based inclusive line numbers."""

    start_line: int
    end_line: int
    text: str


def _find_last_break(window: str) -> int:
    para = window.rfind("\n\n")
    if para >= 0:
        return para + 2
    sentence = max(
        window.rfind(". "),
        window.rfind("? "),
        window.rfind("! "),
        window.rfind(".\n"),
    )
    if sentence >= 0:
        return sentence + 2
    word = window.rfind(" ")
    if word >= 0:
        return word + 1
    return -1


def chunk_text(input: str) -> list[ChunkPiece]:
    text = input.replace("\r\n", "\n").strip()
    if not text:
        return []

    pieces: list[ChunkPiece] = []
    position = 0
    cursor = 0

    while cursor < len(text):
        end = min(cursor + CHUNK_SIZE, len(text))

        if end < len(text):
            window = text[cursor:end]
            last_break = _find_last_break(window)
            if last_break > CHUNK_SIZE * 0.5:
                end = cursor + last_break

        piece = text[cursor:end].strip()
        if piece:
            pieces.append(ChunkPiece(position=position, text=piece))
            position += 1

        if end >= len(text):
            break
        cursor = max(end - CHUNK_OVERLAP, cursor + 1)

    return pieces


def chunk_code_lines(content: str, *, max_lines: int = 60, overlap: int = 10) -> list[CodeChunkPiece]:
    """Split source code into overlapping line windows.

    Line-aligned (not char-aligned) so every chunk carries exact
    ``start_line``/``end_line`` evidence references. Windows break
    preferentially on blank lines near the boundary to avoid
    splitting a block mid-statement.
    """
    lines = content.replace("\r\n", "\n").split("\n")
    # Drop a single trailing empty line produced by a final newline.
    if lines and lines[-1] == "":
        lines.pop()
    if not lines:
        return []

    step = max(1, max_lines - overlap)
    pieces: list[CodeChunkPiece] = []
    start = 0
    total = len(lines)
    while start < total:
        end = min(start + max_lines, total)
        # Snap the boundary back to a nearby blank line to keep blocks coherent.
        if end < total:
            for back in range(end, max(start + step, end - 10), -1):
                if not lines[back - 1].strip():
                    end = back
                    break
        block = "\n".join(lines[start:end]).strip("\n")
        if block.strip():
            pieces.append(CodeChunkPiece(start_line=start + 1, end_line=end, text=block))
        if end >= total:
            break
        start += step
    return pieces
