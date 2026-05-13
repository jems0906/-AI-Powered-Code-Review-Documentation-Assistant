"""
Code Analysis Engine
Parses unified diffs, extracts changed files, runs:
  - AST-based complexity metrics via radon/lizard
  - Dependency change detection
  - Refactoring opportunity detection
"""
from __future__ import annotations

import re
import structlog
from dataclasses import dataclass, field
from typing import List, Optional, Dict

log = structlog.get_logger()


@dataclass
class FileChange:
    path: str
    language: str
    added_lines: List[str] = field(default_factory=list)
    removed_lines: List[str] = field(default_factory=list)
    new_content: str = ""
    cyclomatic_complexity: Optional[float] = None
    cognitive_complexity: Optional[float] = None
    functions_changed: List[str] = field(default_factory=list)
    has_new_imports: bool = False
    import_changes: List[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    files: List[FileChange] = field(default_factory=list)
    total_additions: int = 0
    total_deletions: int = 0
    languages_detected: List[str] = field(default_factory=list)
    high_complexity_functions: List[Dict] = field(default_factory=list)
    dependency_changes: List[str] = field(default_factory=list)


LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".c": "c",
    ".kt": "kotlin",
    ".swift": "swift",
    ".php": "php",
}

DEPENDENCY_FILES = {
    "requirements.txt", "pyproject.toml", "setup.py",
    "package.json", "package-lock.json", "yarn.lock",
    "go.mod", "go.sum", "Cargo.toml", "Gemfile", "pom.xml",
    "build.gradle", "build.gradle.kts",
}


class CodeAnalysisEngine:
    def analyze_diff(self, diff_text: str) -> AnalysisResult:
        result = AnalysisResult()
        if not diff_text:
            return result

        file_changes = self._parse_diff(diff_text)
        for fc in file_changes:
            self._detect_language(fc)
            self._compute_metrics(fc)
            self._detect_import_changes(fc)
            self._detect_function_changes(fc)

            result.files.append(fc)
            result.total_additions += len(fc.added_lines)
            result.total_deletions += len(fc.removed_lines)

            if fc.language and fc.language not in result.languages_detected:
                result.languages_detected.append(fc.language)

            # Flag high complexity
            if fc.cyclomatic_complexity and fc.cyclomatic_complexity > 10:
                result.high_complexity_functions.append({
                    "file": fc.path,
                    "cyclomatic": fc.cyclomatic_complexity,
                })

            # Dependency changes
            filename = fc.path.split("/")[-1]
            if filename in DEPENDENCY_FILES:
                result.dependency_changes.append(fc.path)

        return result

    def _parse_diff(self, diff_text: str) -> List[FileChange]:
        files: List[FileChange] = []
        current: Optional[FileChange] = None
        new_file_lines: List[str] = []

        for line in diff_text.splitlines():
            if line.startswith("diff --git"):
                if current is not None:
                    current.new_content = "\n".join(new_file_lines)
                    files.append(current)
                # Extract path: "diff --git a/foo.py b/foo.py"
                parts = line.split(" b/")
                path = parts[-1] if len(parts) > 1 else "unknown"
                current = FileChange(path=path, language="")
                new_file_lines = []
            elif current is not None:
                if line.startswith("+") and not line.startswith("+++"):
                    content = line[1:]
                    current.added_lines.append(content)
                    new_file_lines.append(content)
                elif line.startswith("-") and not line.startswith("---"):
                    current.removed_lines.append(line[1:])
                elif not line.startswith(("@@", "index ", "---", "+++")):
                    # Context line
                    new_file_lines.append(line[1:] if line.startswith(" ") else line)

        if current is not None:
            current.new_content = "\n".join(new_file_lines)
            files.append(current)

        return files

    def _detect_language(self, fc: FileChange):
        for ext, lang in LANGUAGE_MAP.items():
            if fc.path.endswith(ext):
                fc.language = lang
                return
        fc.language = "unknown"

    def _compute_metrics(self, fc: FileChange):
        if fc.language != "python" or not fc.new_content:
            return
        try:
            import radon.complexity as radon_cc
            blocks = radon_cc.cc_visit(fc.new_content)
            if blocks:
                fc.cyclomatic_complexity = sum(b.complexity for b in blocks) / len(blocks)
        except Exception:
            pass

        try:
            import lizard
            result = lizard.analyze_file.analyze_source_code(fc.path, fc.new_content)
            if result.function_list:
                fc.cognitive_complexity = sum(f.cyclomatic_complexity for f in result.function_list) / len(result.function_list)
        except Exception:
            pass

    def _detect_import_changes(self, fc: FileChange):
        import_pattern = re.compile(r"^(import |from |require\(|#include )")
        for line in fc.added_lines:
            if import_pattern.match(line.strip()):
                fc.has_new_imports = True
                fc.import_changes.append(f"+ {line.strip()}")
        for line in fc.removed_lines:
            if import_pattern.match(line.strip()):
                fc.import_changes.append(f"- {line.strip()}")

    def _detect_function_changes(self, fc: FileChange):
        if fc.language == "python":
            func_pattern = re.compile(r"^def ([a-zA-Z_][a-zA-Z0-9_]*)\s*\(")
        elif fc.language in ("javascript", "typescript"):
            func_pattern = re.compile(r"(?:function\s+([a-zA-Z_][a-zA-Z0-9_]*)|const\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(?:async\s*)?\()")
        else:
            return

        for line in fc.added_lines:
            m = func_pattern.search(line)
            if m:
                name = m.group(1) or m.group(2)
                if name and name not in fc.functions_changed:
                    fc.functions_changed.append(name)
