"""Tests for the free deterministic symbol extractor (Phase 1, stdlib-only)."""
from __future__ import annotations

from app.core.symbols import extract_imports, extract_symbols


def test_python_symbols_find_class_function_method_constant():
    content = (
        "import os\n"
        "\n"
        "MAX_RETRIES = 3\n"
        "\n"
        "def login(user):\n"
        "    return True\n"
        "\n"
        "class AuthService:\n"
        "    def require_auth(self, request):\n"
        "        return request.user\n"
    )
    spans = extract_symbols("app/auth.py", content)
    by_name = {s.qualified_name: s for s in spans}
    assert by_name["MAX_RETRIES"].kind == "constant"
    assert by_name["login"].kind == "function"
    assert by_name["login"].start_line == 5
    assert by_name["login"].end_line == 6  # body stays with the signature
    assert by_name["AuthService"].kind == "class"
    assert by_name["AuthService.require_auth"].kind == "method"


def test_python_broken_syntax_returns_empty_without_raising():
    assert extract_symbols("app/broken.py", "def foo(:\n  broken!!!") == []


def test_binary_and_empty_return_empty():
    assert extract_symbols("app/a.py", "") == []
    assert extract_symbols("app/a.py", "   \n  ") == []
    assert extract_symbols("app/a.py", "def ok():\n\x00binary") == []


def test_typescript_regex_finds_class_and_function():
    content = (
        "export class CartanaLogo {\n"
        "  render() {\n"
        "    return null;\n"
        "  }\n"
        "}\n"
        "\n"
        "export function useQueryState(key) {\n"
        "  return key;\n"
        "}\n"
    )
    spans = extract_symbols("src/logo.tsx", content)
    names = {s.name for s in spans}
    assert "CartanaLogo" in names
    assert "useQueryState" in names
    assert all(s.end_line >= s.start_line for s in spans)


def test_go_regex_finds_func_and_type():
    content = "package main\n\ntype Server struct{}\n\nfunc Start(s *Server) {}\n"
    spans = extract_symbols("cmd/main.go", content)
    names = {s.name for s in spans}
    assert "Server" in names
    assert "Start" in names


def test_extract_imports_lists_modules():
    content = "import os\nfrom app.db import models\nconst x = require('fs');\n"
    imports = extract_imports(content)
    assert any("os" in i for i in imports)


def test_never_raises_on_garbage():
    assert extract_symbols("weird.xyz", "\x01\x02\x03" * 100) == []
    assert extract_imports("\x00") == []
