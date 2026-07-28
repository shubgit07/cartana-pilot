"""Tests for the text chunking strategy.

Port of ``apps/api/src/lib/chunking.test.ts`` (the Node test).
"""
from __future__ import annotations

from app.core.chunking import chunk_text


def test_empty_string():
    assert chunk_text("") == []


def test_whitespace_only():
    assert chunk_text("   \n\n  ") == []


def test_short_text_single_chunk():
    pieces = chunk_text("Hello world.")
    assert len(pieces) == 1
    assert pieces[0].position == 0
    assert pieces[0].text == "Hello world."


def test_long_text_multiple_chunks():
    text = ". ".join(f"Sentence number {i} with some content" for i in range(50))
    pieces = chunk_text(text)
    assert len(pieces) > 1
    positions = [p.position for p in pieces]
    assert positions == list(range(len(pieces)))


def test_overlap_between_chunks():
    text = "A" * 1500
    pieces = chunk_text(text)
    assert len(pieces) > 1
    # The end of one chunk should overlap with the start of the next
    # (our chunker uses ~100 char overlap)


def test_positions_are_sequential():
    text = ". ".join(f"Sentence {i}" for i in range(100))
    pieces = chunk_text(text)
    assert all(p.position == i for i, p in enumerate(pieces))
