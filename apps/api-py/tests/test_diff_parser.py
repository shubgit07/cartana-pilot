"""Unit tests for Stage 1 Git Diff Parser and Noise Stripper.

Tests that lockfiles, minified JS/CSS, images, and build directories are stripped out
to achieve 70-80% token reduction before LLM ingestion.
"""
from __future__ import annotations

from app.core.diff_parser import is_ignored_file, parse_unified_diff

SAMPLE_RAW_DIFF = """diff --git a/package-lock.json b/package-lock.json
index 1234567..89abcdef 100644
--- a/package-lock.json
+++ b/package-lock.json
@@ -1,5 +1,5 @@
 {
-  "name": "cartana",
+  "name": "cartana-monorepo",
   "version": "1.0.0"
 }
diff --git a/public/logo.svg b/public/logo.svg
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/public/logo.svg
@@ -0,0 +1 @@
+<svg><path d="M0 0h10v10H0z"/></svg>
diff --git a/apps/api-py/app/api/routes/auth.py b/apps/api-py/app/api/routes/auth.py
new file mode 100644
index 0000000..abcdef1
--- /dev/null
+++ b/apps/api-py/app/api/routes/auth.py
@@ -0,0 +1,5 @@
+from fastapi import APIRouter
+
+router = APIRouter()
+
+@router.post("/login")
+def login():
+    return {"status": "ok"}
diff --git a/apps/web/src/features/auth/Login.tsx b/apps/web/src/features/auth/Login.tsx
index 1111111..2222222 100644
--- a/apps/web/src/features/auth/Login.tsx
+++ b/apps/web/src/features/auth/Login.tsx
@@ -1,3 +1,5 @@
 export function Login() {
-  return <div>Login</div>;
+  return <form>Login Form</form>;
 }
"""


def test_is_ignored_file():
    assert is_ignored_file("package-lock.json") is True
    assert is_ignored_file("yarn.lock") is True
    assert is_ignored_file("pnpm-lock.yaml") is True
    assert is_ignored_file("assets/banner.png") is True
    assert is_ignored_file("public/icon.svg") is True
    assert is_ignored_file("dist/bundle.min.js") is True
    assert is_ignored_file(".next/server/app.js") is True
    assert is_ignored_file("node_modules/express/index.js") is True

    # Real code files must NOT be ignored
    assert is_ignored_file("apps/api-py/app/api/routes/auth.py") is False
    assert is_ignored_file("apps/web/src/features/auth/Login.tsx") is False
    assert is_ignored_file("packages/shared/src/types.ts") is False


def test_parse_unified_diff_strips_noise():
    summary = parse_unified_diff(SAMPLE_RAW_DIFF)

    assert summary.total_files == 4
    assert summary.ignored_files == 2  # package-lock.json + logo.svg
    assert summary.kept_files == 2     # auth.py + Login.tsx

    filenames = [f.filename for f in summary.files]
    assert "apps/api-py/app/api/routes/auth.py" in filenames
    assert "apps/web/src/features/auth/Login.tsx" in filenames
    assert "package-lock.json" not in filenames
    assert "public/logo.svg" not in filenames

    assert "FILE: apps/api-py/app/api/routes/auth.py" in summary.compressed_text
    assert "FILE: apps/web/src/features/auth/Login.tsx" in summary.compressed_text
    assert "package-lock.json" not in summary.compressed_text
