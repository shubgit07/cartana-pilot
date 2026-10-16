"""Text chunking strategy.

Port of ``apps/api/src/modules/sources/chunking.ts``.

~700 chars per chunk with ~100 char overlap. Prefers paragraph > sentence >
word boundaries. Deliberately naive — smarter strategies can replace this
function without changing callers.

Code chunking is symbol-aware (Phase 1, free, stdlib-only): when caller
supplies symbol spans, one chunk per symbol keeps signatures with bodies;
large symbols fall back to line windows. Without symbols the original
line-window behaviour is preserved byte-for-byte.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # avoid runtime import cycle; symbols.py never imports chunking
    from app.core.symbols import SymbolSpan

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


def _split_line_window(
    lines: list[str], *, start: int, end: int, max_lines: int, overlap: int
) -> list[CodeChunkPiece]:
    """Split lines[start:end] (0-based, end exclusive) into blank-line-snapped windows."""
    pieces: list[CodeChunkPiece] = []
    step = max(1, max_lines - overlap)
    cursor = start
    while cursor < end:
        window_end = min(cursor + max_lines, end)
        # Snap the boundary back to a nearby blank line to keep blocks coherent.
        if window_end < end:
            for back in range(window_end, max(cursor + step, window_end - 10), -1):
                if not lines[back - 1].strip():
                    window_end = back
                    break
        block = "\n".join(lines[cursor:window_end]).strip("\n")
        if block.strip():
            pieces.append(CodeChunkPiece(start_line=cursor + 1, end_line=window_end, text=block))
        if window_end >= end:
            break
        # Guard against zero-progress when a blank-line snap lands on cursor.
        cursor = max(window_end - overlap, cursor + 1) if window_end > cursor else cursor + 1
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

    return _split_line_window(lines, start=0, end=len(lines), max_lines=max_lines, overlap=overlap)


def chunk_code_with_symbols(
    content: str,
    symbols: list[SymbolSpan] | None,
    *,
    max_lines: int = 60,
    overlap: int = 10,
) -> list[CodeChunkPiece]:
    """Symbol-aware code chunking; falls back to line windows when symbols are thin.

    Rules:
    - ``None``/empty symbols, a single symbol, or coverage <30% of lines
      → plain :func:`chunk_code_lines` (byte-identical fallback).
    - Each symbol becomes its own chunk so signatures stay with bodies.
      Regex-extracted single-line symbols expand to the next symbol start
      (capped at ``max_lines``) to capture the body without a parser.
    - Symbols longer than ``max_lines`` split internally with blank-line
      snapping; gaps between symbols (headers, module glue) chunk normally.
    - Never raises; any internal error returns the line-window fallback.
    """
    try:
        lines = content.replace("\r\n", "\n").split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        total = len(lines)
        if not lines or not symbols:
            return chunk_code_lines(content, max_lines=max_lines, overlap=overlap)

        spans = sorted(
            [s for s in symbols if s.start_line >= 1 and s.end_line >= s.start_line],
            key=lambda s: s.start_line,
        )
        if len(spans) <= 1:
            return chunk_code_lines(content, max_lines=max_lines, overlap=overlap)
        covered = sum(min(s.end_line, total) - s.start_line + 1 for s in spans if s.start_line <= total)
        if covered < total * 0.3:
            return chunk_code_lines(content, max_lines=max_lines, overlap=overlap)

        pieces: list[CodeChunkPiece] = []
        cursor = 0  # 0-based next uncovered line
        for idx, span in enumerate(spans):
            s0 = max(1, span.start_line)
            # Expand single-line (regex) symbols to the next symbol start.
            if span.end_line <= span.start_line and idx + 1 < len(spans):
                expanded_end = min(spans[idx + 1].start_line - 1, s0 + max_lines - 1, total)
                s1 = max(expanded_end, s0)
            else:
                s1 = min(span.end_line, total)
            if s0 > total:
                continue
            # Gap before this symbol (file header / glue between defs).
            if cursor < s0 - 1:
                pieces.extend(_split_line_window(
                    lines, start=cursor, end=s0 - 1, max_lines=max_lines, overlap=overlap
                ))
            # Symbol body itself.
            if s1 - s0 + 1 <= max_lines:
                block = "\n".join(lines[s0 - 1 : s1]).strip("\n")
                if block.strip():
                    pieces.append(CodeChunkPiece(start_line=s0, end_line=s1, text=block))
            else:
                pieces.extend(_split_line_window(
                    lines, start=s0 - 1, end=s1, max_lines=max_lines, overlap=overlap
                ))
            cursor = max(cursor, s1)
        if cursor < total:
            pieces.extend(_split_line_window(
                lines, start=cursor, end=total, max_lines=max_lines, overlap=overlap
            ))
        return pieces or chunk_code_lines(content, max_lines=max_lines, overlap=overlap)
    except Exception:  # noqa: BLE001 — symbol chunking degrades to line windows
        return chunk_code_lines(content, max_lines=max_lines, overlap=overlap)
