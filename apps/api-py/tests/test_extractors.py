"""Tests for requirement extraction."""
from __future__ import annotations

from app.providers.ai_provider import AIExtractRequirementsInput
from app.providers.extractors.requirement_extractor import extract_requirements_stub

# ---- Requirement extractor ----


def test_requirement_extractor_finds_must():
    chunks = [{"id": "c1", "position": 0, "text": "The system must support single sign-on via SAML 2.0."}]
    result = extract_requirements_stub(
        AIExtractRequirementsInput(sourceFilename="spec.pdf", chunks=chunks)
    )
    assert len(result) >= 1
    assert "must" in result[0].description.lower()


def test_requirement_extractor_finds_shall():
    chunks = [{"id": "c1", "position": 0, "text": "The API shall return JSON responses."}]
    result = extract_requirements_stub(
        AIExtractRequirementsInput(sourceFilename="spec.pdf", chunks=chunks)
    )
    assert len(result) >= 1


def test_requirement_extractor_skips_non_requirements():
    chunks = [{"id": "c1", "position": 0, "text": "The weather is nice today."}]
    result = extract_requirements_stub(
        AIExtractRequirementsInput(sourceFilename="spec.pdf", chunks=chunks)
    )
    assert len(result) == 0


def test_requirement_extractor_dedupes():
    text = "The system must support SSO. The system must support SSO."
    chunks = [{"id": "c1", "position": 0, "text": text}]
    result = extract_requirements_stub(
        AIExtractRequirementsInput(sourceFilename="spec.pdf", chunks=chunks)
    )
    assert len(result) == 1


# ---- Clean text & transcript preprocessor ----


def test_clean_document_text_transcripts():
    from app.core.clean_text import clean_document_text

    raw_transcript = (
        "Alex [00:12:34]: We must support single sign-on via SAML 2.0.\n"
        "Speaker 1: (01:25) The system shall return JSON error payloads.\n"
        "Page 1 of 5\n"
        "Confidential & Proprietary\n"
    )

    cleaned = clean_document_text(raw_transcript)
    assert "[00:12:34]" not in cleaned
    assert "(01:25)" not in cleaned
    assert "Alex:" not in cleaned
    assert "Speaker 1:" not in cleaned
    assert "Page 1 of 5" not in cleaned
    assert "We must support single sign-on via SAML 2.0." in cleaned
    assert "The system shall return JSON error payloads." in cleaned

