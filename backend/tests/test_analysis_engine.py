"""
Tests for the code analysis engine.
"""
from app.analysis.engine import CodeAnalysisEngine

SAMPLE_DIFF = """diff --git a/app/utils.py b/app/utils.py
index abc1234..def5678 100644
--- a/app/utils.py
+++ b/app/utils.py
@@ -1,5 +1,15 @@
+import os
+import hashlib
+
 def hello():
-    pass
+    return "hello"
+
+def compute_hash(data: str) -> str:
+    \"\"\"Return SHA-256 hex digest of data.\"\"\"
+    return hashlib.sha256(data.encode()).hexdigest()
+
+def risky_eval(code: str):
+    eval(code)
"""


def test_parse_diff_finds_file():
    engine = CodeAnalysisEngine()
    result = engine.analyze_diff(SAMPLE_DIFF)
    assert len(result.files) == 1
    assert result.files[0].path == "app/utils.py"


def test_language_detected():
    engine = CodeAnalysisEngine()
    result = engine.analyze_diff(SAMPLE_DIFF)
    assert result.files[0].language == "python"


def test_import_changes_detected():
    engine = CodeAnalysisEngine()
    result = engine.analyze_diff(SAMPLE_DIFF)
    fc = result.files[0]
    assert fc.has_new_imports is True
    assert any("import os" in imp for imp in fc.import_changes)


def test_function_changes_detected():
    engine = CodeAnalysisEngine()
    result = engine.analyze_diff(SAMPLE_DIFF)
    fc = result.files[0]
    assert "compute_hash" in fc.functions_changed or "risky_eval" in fc.functions_changed


def test_additions_and_deletions():
    engine = CodeAnalysisEngine()
    result = engine.analyze_diff(SAMPLE_DIFF)
    assert result.total_additions > 0
    assert result.total_deletions > 0


def test_empty_diff():
    engine = CodeAnalysisEngine()
    result = engine.analyze_diff("")
    assert result.files == []
    assert result.total_additions == 0
