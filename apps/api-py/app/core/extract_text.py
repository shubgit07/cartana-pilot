"""Text extraction from uploaded files.

Port of ``apps/api/src/modules/sources/extractText.ts``.

Supports PDF (via pdfplumber) and plain text. Image/screenshot ingestion is
future expansion.
"""
from __future__ import annotations

import logging
from typing import Literal

logger = logging.getLogger(__name__)

SourceKindType = Literal["pdf", "text"]


def extract_text(data: bytes, kind: SourceKindType) -> str:
    """Extract text content from a raw file buffer."""
    if kind == "text":
        return data.decode("utf-8", errors="replace")

    if kind == "pdf":
        try:
            import pdfplumber
        except ImportError as exc:
            raise RuntimeError(
                "pdfplumber is required for PDF extraction. Install it with: pip install pdfplumber"
            ) from exc

        import io

        try:
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                texts = [page.extract_text() or "" for page in pdf.pages]
                return "\n\n".join(texts)
        except Exception as exc:
            logger.error("PDF parse failed: %s", exc)
            raise

    raise ValueError(f"Unsupported source kind: {kind}")
