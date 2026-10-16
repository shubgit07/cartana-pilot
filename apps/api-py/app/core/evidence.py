"""Deterministic evidence validation for PR Trust Brief verdicts.

Every evidence claim the model returns is checked against the real diff
(or the retrieved repository context) before it can reach the brief. A
claim whose file is not a changed file, or whose snippet cannot be found
in that file's diff content, is marked unverified and its verdict is
downgraded to ``unclear``. No model is involved in this module.
"""
from __future__ import annotations

from app.api.schemas.audit import RequirementVerificationVerdict
from app.core.diff_parser import ChangedFileDiff

UNVERIFIED_PREFIX = "evidence not found in the diff: "


def normalize_path(path: str) -> str:
    """Case-insensitive, prefix-free path form used for file matching."""
    cleaned = path.strip().replace("\\", "/")
    for prefix in ("a/", "b/", "./"):
        while cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix) :]
    return cleaned.lower()


def _normalize_line(line: str) -> str:
    """Strip one diff marker and surrounding whitespace from a line."""
    stripped = line.strip()
    if stripped[:1] in ("+", "-"):
        stripped = stripped[1:].strip()
    return stripped


def _normalize_text(text: str) -> str:
    """Normalized corpus: markers and indentation stripped, blanks dropped."""
    lines = [_normalize_line(line) for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def build_diff_index(parsed_files: list[ChangedFileDiff]) -> dict[str, str]:
    """Map every changed path (old and new) to its normalized diff content."""
    index: dict[str, str] = {}
    for parsed_file in parsed_files:
        lines: list[str] = []
        for hunk in parsed_file.hunks:
            lines.extend(hunk.added_lines)
            lines.extend(hunk.removed_lines)
        corpus = _normalize_text("\n".join(lines))
        for path in (parsed_file.filename, parsed_file.old_path, parsed_file.new_path):
            if path and path != "/dev/null":
                index.setdefault(normalize_path(path), corpus)
    return index


def snippet_found_in(snippet: str, corpus: str) -> bool:
    """True when the snippet matches the corpus as a block or line by line."""
    lines = [_normalize_line(line) for line in snippet.splitlines()]
    lines = [line for line in lines if line]
    if not lines or not corpus:
        return False
    if "\n".join(lines) in corpus:
        return True
    return all(line in corpus for line in lines)


def validate_evidence(
    verdicts: list[RequirementVerificationVerdict],
    diff_index: dict[str, str],
    repo_context: str = "",
) -> tuple[list[RequirementVerificationVerdict], int, int]:
    """Check every evidence claim against the diff or repository context.

    Returns ``(checked_verdicts, verified_count, unverified_count)``.
    Verdicts that claim no evidence (``missing``/``unclear``) are left as
    they are with a ``None`` flag. A covered/partial verdict whose evidence
    cannot be found is downgraded to ``unclear`` with low confidence and a
    prefixed rationale, so unverified claims never count toward coverage.
    """
    repo_corpus = _normalize_text(repo_context) if repo_context else ""
    checked: list[RequirementVerificationVerdict] = []
    verified = 0
    unverified = 0

    for verdict in verdicts:
        claims_evidence = bool(verdict.evidenceFile and verdict.evidenceSnippet)
        if not claims_evidence:
            checked.append(verdict.model_copy(update={"evidenceVerified": None}))
            continue

        corpus = diff_index.get(normalize_path(verdict.evidenceFile))
        if corpus is not None:
            is_verified = snippet_found_in(verdict.evidenceSnippet, corpus)
        elif repo_corpus and verdict.evidenceFile.strip() in repo_context:
            is_verified = snippet_found_in(verdict.evidenceSnippet, repo_corpus)
        else:
            is_verified = False

        if is_verified:
            verified += 1
            checked.append(verdict.model_copy(update={"evidenceVerified": True}))
            continue

        unverified += 1
        update: dict[str, object] = {"evidenceVerified": False}
        if verdict.status in ("covered", "partial"):
            update["status"] = "unclear"
            update["confidence"] = "low"
            update["rationale"] = UNVERIFIED_PREFIX + verdict.rationale
        checked.append(verdict.model_copy(update=update))

    return checked, verified, unverified


def compute_coverage_score(
    verdicts: list[RequirementVerificationVerdict],
) -> int:
    """Deterministic coverage: covered counts 1, partial counts 0.5."""
    if not verdicts:
        return 0
    weighted = sum(
        1.0 if v.status == "covered" else 0.5 if v.status == "partial" else 0.0
        for v in verdicts
    )
    return round(100 * weighted / len(verdicts))


def compute_trust_level(
    verdicts: list[RequirementVerificationVerdict],
    risk_alerts: list,
    coverage_score: int,
) -> str:
    """Deterministic trust level from verdicts, alerts, and the score.

    low: score below 50 or any critical risk alert.
    high: score at or above 80 with no missing verdict, no unverified
    evidence, and no critical alert.
    medium: everything else.
    """
    has_critical = any(getattr(a, "severity", "") == "critical" for a in risk_alerts)
    has_missing = any(v.status == "missing" for v in verdicts)
    has_unverified = any(v.evidenceVerified is False for v in verdicts)

    if coverage_score < 50 or has_critical:
        return "low"
    if coverage_score >= 80 and not has_missing and not has_unverified and not has_critical:
        return "high"
    return "medium"
