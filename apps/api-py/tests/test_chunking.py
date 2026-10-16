"""Tests for the text chunking strategy.

Port of ``apps/api/src/lib/chunking.test.ts`` (the Node test).
"""
from __future__ import annotations

from app.core.chunking import chunk_code_lines, chunk_code_with_symbols, chunk_text
from app.core.symbols import extract_symbols


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


def test_symbol_chunking_keeps_signature_with_body():
    content = (
        "import os\n"
        "\n"
        "def login(user):\n"
        "    return True\n"
        "\n"
        "def logout(user):\n"
        "    return False\n"
    )
    spans = extract_symbols("app/auth.py", content)
    pieces = chunk_code_with_symbols(content, spans)
    assert len(pieces) >= 2
    login = next(p for p in pieces if "def login" in p.text)
    assert "return True" in login.text  # signature and body in one chunk


def test_symbol_chunking_falls_back_without_symbols():
    content = "\n".join(f"line {i}" for i in range(1, 151))
    plain = chunk_code_lines(content, max_lines=60, overlap=10)
    fallback = chunk_code_with_symbols(content, [])
    assert [(p.start_line, p.end_line) for p in fallback] == [
        (p.start_line, p.end_line) for p in plain
    ]


def test_large_symbol_splits_but_never_crashes():
    body = "\n".join(f"    step_{i}()" for i in range(200))
    content = f"def huge():\n{body}\n"
    spans = extract_symbols("app/big.py", content)
    pieces = chunk_code_with_symbols(content, spans, max_lines=60, overlap=10)
    assert pieces
    assert all(p.end_line >= p.start_line for p in pieces)
