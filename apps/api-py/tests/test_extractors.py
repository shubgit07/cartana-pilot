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


'''Removed standalone task and requirement-to-task coverage tests.


def test_task_extractor_finds_action_verbs():
    chunks = [{"id": "c1", "position": 0, "text": "Build the authentication service."}]
    result = extract_tasks_stub(
        AIExtractTasksInput(sourceFilename="spec.pdf", chunks=chunks, requirements=[])
    )
    assert len(result) >= 1
    assert result[0].title.startswith("Build")


def test_task_extractor_finds_create():
    chunks = [{"id": "c1", "position": 0, "text": "Create a dashboard for monitoring."}]
    result = extract_tasks_stub(
        AIExtractTasksInput(sourceFilename="spec.pdf", chunks=chunks, requirements=[])
    )
    assert len(result) >= 1


def test_task_extractor_skips_non_actions():
    chunks = [{"id": "c1", "position": 0, "text": "The system is very fast."}]
    result = extract_tasks_stub(
        AIExtractTasksInput(sourceFilename="spec.pdf", chunks=chunks, requirements=[])
    )
    assert len(result) == 0


def test_task_extractor_links_to_requirement():
    chunks = [{"id": "c1", "position": 0, "text": "Implement SSO authentication for users."}]
    reqs = [{"title": "Must support SSO", "description": ""}]
    result = extract_tasks_stub(
        AIExtractTasksInput(sourceFilename="spec.pdf", chunks=chunks, requirements=reqs)
    )
    assert len(result) >= 1
    assert result[0].linkedRequirementTitle is not None


# ---- Coverage stub ----


def test_coverage_stub_missing():
    result = coverage_stub(AIAuditCoverageInput(
        requirement={"title": "Must support SSO", "description": ""},
        candidateTasks=[],
    ))
    assert len(result.judgments) == 1
    assert result.judgments[0].status == "missing"


def test_coverage_stub_covered():
    result = coverage_stub(AIAuditCoverageInput(
        requirement={"title": "Must support SSO authentication via SAML", "description": "The system must support SSO"},
        candidateTasks=[{"title": "Implement SSO authentication via SAML", "description": "Build SSO auth"}],
    ))
    assert len(result.judgments) == 1
    assert result.judgments[0].status in ("covered", "partial")


def test_coverage_stub_unclear():
    result = coverage_stub(AIAuditCoverageInput(
        requirement={"title": "Must support SSO", "description": ""},
        candidateTasks=[{"title": "Design the database schema", "description": "Create tables"}],
    ))
    assert len(result.judgments) == 1
    assert result.judgments[0].status == "unclear"
'''


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

