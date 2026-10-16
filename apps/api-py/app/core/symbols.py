"""Free deterministic symbol extraction for code retrieval (Phase 1).

Zero-dependency, stdlib-only: ``ast`` for Python, line-regex for other
languages. No network, no model, no new pip package — safe to run inside
the indexer without starting any backend service.

Design:
- ``extract_symbols(path, content)`` never raises; unparseable or
  unsupported files return ``[]`` so indexing degrades to line windows.
- Python uses the real AST so method signatures are never split from
  bodies at the symbol layer; other languages use conservative regexes
  tuned for recall over precision (false positives are harmless — they
  only add boost candidates, never verdicts).
- Output preserves exact 1-based ``start_line``/``end_line`` so chunks
  and evidence references stay joinable by line numbers.
"""
from __future__ import annotations

import ast
import hashlib
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SymbolSpan:
    """One defined symbol with exact source lines."""

    kind: str  # matches SymbolKind values: class/function/method/...
    name: str
    qualified_name: str
    signature: str | None
    start_line: int
    end_line: int

    @property
    def symbol_hash(self) -> str:
        return hashlib.sha256(
            f"{self.qualified_name}:{self.start_line}:{self.end_line}".encode()
        ).hexdigest()


_MAX_FILE_CHARS = 500_000

_PY_IMPORT_RE = re.compile(r"^\s*(?:import\s+(.+)|from\s+(\S+)\s+import\s+(.+))")

# Conservative per-language definition patterns: (kind, regex with (?P<name>...)).
_DEF_PATTERNS: dict[str, list[tuple[str, re.Pattern[str]]]] = {
    "javascript": [
        ("class", re.compile(r"^\s*(?:export\s+)?(?:default\s+)?class\s+(?P<name>[A-Za-z_$][\w$]*)")),
        ("function", re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+(?P<name>[A-Za-z_$][\w$]*)")),
        ("function", re.compile(r"^\s*(?:export\s+)?const\s+(?P<name>[A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\(|[^=]*=>)")),
        ("interface", re.compile(r"^\s*(?:export\s+)?interface\s+(?P<name>[A-Za-z_$][\w$]*)")),
        ("type", re.compile(r"^\s*(?:export\s+)?type\s+(?P<name>[A-Za-z_$][\w$]*)\s*=")),
    ],
    "go": [
        ("function", re.compile(r"^\s*func\s+(?:\([^)]*\)\s*)?(?P<name>[A-Za-z_]\w*)\s*\(")),
        ("type", re.compile(r"^\s*type\s+(?P<name>[A-Za-z_]\w*)\s+(?:struct|interface|[\w\[\]\*])")),
    ],
    "java": [
        ("class", re.compile(r"^\s*(?:public|private|protected|static|final|abstract|\s)*(?:class|record)\s+(?P<name>[A-Za-z_]\w*)")),
        ("interface", re.compile(r"^\s*(?:public|\s)*interface\s+(?P<name>[A-Za-z_]\w*)")),
        ("method", re.compile(r"^\s*(?:public|private|protected|static|final|async|\s)+(?:[\w<>\[\]]+\s+)(?P<name>[A-Za-z_]\w*)\s*\(")),
    ],
    "generic": [
        ("class", re.compile(r"^\s*class\s+(?P<name>[A-Za-z_]\w*)")),
        ("function", re.compile(r"^\s*(?:def|fn|function|sub)\s+(?P<name>[A-Za-z_]\w*)")),
    ],
}

_EXT_TO_FAMILY = {
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "javascript", ".tsx": "javascript", ".mts": "javascript",
    ".go": "go",
    ".java": "java", ".kt": "java", ".cs": "java", ".php": "java", ".swift": "java",
    ".rb": "generic", ".rs": "generic", ".py": "python",
    ".c": "generic", ".h": "generic", ".cpp": "generic", ".sh": "generic", ".sql": "generic",
}


def _family_for_path(path: str) -> str:
    dot = path.rfind(".")
    if dot < 0:
        return "generic"
    return _EXT_TO_FAMILY.get(path[dot:].lower(), "generic")


def extract_symbols(path: str, content: str, *, language: str | None = None) -> list[SymbolSpan]:
    """Extract defined symbols from one file. Never raises; [] on failure."""
    try:
        if not content or not content.strip() or "\x00" in content:
            return []
        if len(content) > _MAX_FILE_CHARS:
            return []
        family = _family_for_path(path)
        if family == "python" or (language or "").lower() == "python" or path.endswith(".py"):
            return _extract_python_symbols(content)
        return _extract_regex_symbols(content, family)
    except Exception:  # noqa: BLE001 — extraction must degrade, not crash sync
        return []


def extract_imports(content: str, *, limit: int = 50) -> list[str]:
    """Best-effort import list for boost context. Never raises."""
    try:
        out: list[str] = []
        for line in content.split("\n"):
            m = _PY_IMPORT_RE.match(line)
            if m:
                mod = (m.group(2) or m.group(1) or "").strip().split()[0].strip(",;")
                if mod:
                    out.append(mod[:200])
            elif line.strip().startswith(("import ", "require(", "from ")):
                out.append(line.strip()[:200])
            if len(out) >= limit:
                break
        return out
    except Exception:  # noqa: BLE001 — import listing is best-effort
        return []


def _extract_python_symbols(content: str) -> list[SymbolSpan]:
    try:
        tree = ast.parse(content)
    except (SyntaxError, ValueError):
        return []
    spans: list[SymbolSpan] = []

    def _sig(args: ast.arguments) -> str | None:
        try:
            return ast.unparse(args)
        except Exception:  # noqa: BLE001 — signature rendering is best-effort
            return None

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            end = getattr(node, "end_lineno", None) or node.lineno
            spans.append(SymbolSpan(
                kind="class", name=node.name, qualified_name=node.name,
                signature=None, start_line=node.lineno, end_line=end,
            ))
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    iend = getattr(item, "end_lineno", None) or item.lineno
                    spans.append(SymbolSpan(
                        kind="method", name=item.name,
                        qualified_name=f"{node.name}.{item.name}",
                        signature=_sig(item.args),
                        start_line=item.lineno, end_line=iend,
                    ))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = getattr(node, "end_lineno", None) or node.lineno
            spans.append(SymbolSpan(
                kind="function", name=node.name, qualified_name=node.name,
                signature=_sig(node.args), start_line=node.lineno, end_line=end,
            ))
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper() and len(target.id) > 1:
                    spans.append(SymbolSpan(
                        kind="constant", name=target.id, qualified_name=target.id,
                        signature=None, start_line=target.lineno, end_line=target.lineno,
                    ))
    spans.sort(key=lambda s: s.start_line)
    return spans


def _extract_regex_symbols(content: str, family: str) -> list[SymbolSpan]:
    patterns = _DEF_PATTERNS.get(family, _DEF_PATTERNS["generic"])
    lines = content.split("\n")
    spans: list[SymbolSpan] = []
    seen: set[tuple[str, int]] = set()
    for idx, line in enumerate(lines, start=1):
        if len(line.strip()) < 3 or len(line) > 500:
            continue
        for kind, rx in patterns:
            try:
                m = rx.match(line)
            except Exception as exc:  # noqa: BLE001 — one bad pattern skips one line
                logger.debug("Symbol pattern failed (path line skipped): %s", exc)
                continue
            if m:
                name = (m.groupdict().get("name") or "").strip()
                if name and (name, idx) not in seen:
                    seen.add((name, idx))
                    spans.append(SymbolSpan(
                        kind=kind, name=name, qualified_name=name,
                        signature=line.strip()[:300],
                        start_line=idx, end_line=idx,
                    ))
                break
    return spans
