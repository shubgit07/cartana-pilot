"""Text and Transcript Noise Preprocessor.

Cleans conversational video/audio transcripts (Zoom, Otter, Whisper, Teams) and
noisy document dumps (PDF footers, page numbers) before LLM requirement extraction.
"""
from __future__ import annotations

import re

# Match timestamps like [00:12:34], (01:23), 12:34 - , 0:15
TIMESTAMP_RE = re.compile(
    r"\[?\b\d{1,2}:\d{2}(?::\d{2})?\b\]?\s*(?:-|–|—)?\s*",
    re.IGNORECASE,
)

# Match speaker tags like "Speaker 1:", "Alex (00:12):", "[John Doe]:", "Sarah:"
SPEAKER_RE = re.compile(
    r"^(?:\[?[A-Z][a-z0-9_\s\.\-]{1,25}\]?\s*(?:\(\d{1,2}:\d{2}\))?:)\s*",
    re.MULTILINE,
)

# Match PDF page footers like "Page 1 of 12", "Page 5", "Confidential & Proprietary"
PDF_FOOTER_RE = re.compile(
    r"^\s*(?:page\s+\d+(?:\s+of\s+\d+)?|confidential(?:\s+and\s+proprietary)?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def strip_transcript_timestamps(text: str) -> str:
    """Strips timestamps like [00:12:34], (01:23), and 12:34 from text."""
    return TIMESTAMP_RE.sub("", text)


def strip_speaker_labels(text: str) -> str:
    """Strips speaker tags like 'Alex:', 'Speaker 1:', and '[John Doe]:'."""
    return SPEAKER_RE.sub("", text)


def clean_document_text(raw_text: str) -> str:
    """Cleans noisy document dumps and video transcripts for LLM ingestion.

    1. Removes timestamps and speaker labels.
    2. Strips PDF page headers/footers.
    3. Normalizes excessive empty lines.
    """
    if not raw_text:
        return ""

    text = strip_transcript_timestamps(raw_text)
    text = strip_speaker_labels(text)
    text = PDF_FOOTER_RE.sub("", text)

    # Normalize multiple newlines into max 2
    lines = [line.strip() for line in text.splitlines()]
    cleaned_lines = []
    empty_count = 0

    for line in lines:
        if not line:
            empty_count += 1
            if empty_count <= 2:
                cleaned_lines.append("")
        else:
            empty_count = 0
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()
