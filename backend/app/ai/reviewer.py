"""
AI Reviewer — dispatches to OpenAI or Anthropic based on config,
parses structured JSON responses into ReviewComment objects.
"""
from __future__ import annotations

import json
import re
import structlog
from dataclasses import dataclass
from typing import List, Optional

from app.core.config import settings
from app.analysis.engine import AnalysisResult

log = structlog.get_logger()

PROFILE_INSTRUCTIONS = {
    "pedantic": (
        "Be thorough and flag everything: style nits, minor inefficiencies, "
        "missing docstrings, naming conventions, and all edge cases."
    ),
    "balanced": (
        "Focus on real bugs, security issues, performance problems, and "
        "important best-practice violations. Skip minor style nits."
    ),
    "relaxed": (
        "Only flag critical bugs, security vulnerabilities, and severe "
        "performance issues. Ignore style and minor improvements."
    ),
}

SYSTEM_PROMPT = """You are an expert code reviewer. Analyze the provided git diff and return a JSON object with this exact schema:

{
  "quality_score": <float 0-10>,
  "summary": "<overall review summary in markdown>",
  "generated_docs": "<markdown documentation for new/changed functions>",
    "generated_tests": "<unit test code (or pseudo-tests) for new/changed functions>",
  "comments": [
    {
      "file_path": "<path>",
      "line_start": <int or null>,
      "line_end": <int or null>,
      "category": "<security|performance|best_practice|edge_case|documentation|style>",
      "severity": "<critical|high|medium|low|info>",
      "body": "<detailed explanation with code context>",
      "suggested_fix": "<corrected code snippet or null>",
      "suggested_diff": "<unified diff showing the fix or null>"
    }
  ]
}

Return ONLY the JSON — no markdown fences, no extra text."""


@dataclass
class AIComment:
    file_path: str
    category: str
    severity: str
    body: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    suggested_fix: Optional[str] = None
    suggested_diff: Optional[str] = None


@dataclass
class AIReviewResult:
    quality_score: float
    summary: str
    generated_docs: str
    generated_tests: str
    comments: List[AIComment]
    provider: str


class AIReviewer:
    async def review(
        self,
        diff: str,
        analysis: AnalysisResult,
        profile: str = "balanced",
        repository_language: Optional[str] = None,
        feedback_learning_context: Optional[str] = None,
    ) -> AIReviewResult:
        profile_note = PROFILE_INSTRUCTIONS.get(profile, PROFILE_INSTRUCTIONS["balanced"])
        user_content = self._build_user_prompt(
            diff,
            analysis,
            profile_note,
            repository_language,
            feedback_learning_context,
        )

        provider = settings.DEFAULT_AI_PROVIDER
        if provider == "anthropic" and settings.ANTHROPIC_API_KEY:
            raw = await self._call_anthropic(user_content)
            parsed = self._parse_response(raw, provider)
        elif settings.OPENAI_API_KEY:
            raw = await self._call_openai(user_content)
            parsed = self._parse_response(raw, provider)
        else:
            log.warning("No AI provider configured, returning stub review")
            parsed = self._stub_result()

        return self._ensure_generated_tests(parsed, analysis, repository_language)

    def _build_user_prompt(
        self,
        diff: str,
        analysis: AnalysisResult,
        profile_note: str,
        repository_language: Optional[str],
        feedback_learning_context: Optional[str],
    ) -> str:
        complexity_info = ""
        if analysis.high_complexity_functions:
            items = ", ".join(f"{h['file']} (CC={h['cyclomatic']:.1f})" for h in analysis.high_complexity_functions)
            complexity_info = f"\nHigh-complexity areas detected: {items}"

        dep_info = ""
        if analysis.dependency_changes:
            dep_info = f"\nDependency files changed: {', '.join(analysis.dependency_changes)}"

        primary_language = self._infer_primary_language(analysis, repository_language)
        test_guidance = ""
        if primary_language != "unknown":
            test_guidance = (
                f"\nPrimary repository language: {primary_language}. "
                "Generate tests in this language using its most common test framework."
            )

        feedback_guidance = ""
        if feedback_learning_context:
            feedback_guidance = (
                "\nDeveloper feedback learning context (use this to calibrate suggestions): "
                f"{feedback_learning_context}"
            )

        max_diff_chars = 28000  # stay within context limits
        truncated_diff = diff[:max_diff_chars] + ("\n...[diff truncated]" if len(diff) > max_diff_chars else "")

        return (
            f"Review profile: {profile_note}\n"
            f"{complexity_info}{dep_info}{test_guidance}{feedback_guidance}\n\n"
            f"--- DIFF ---\n{truncated_diff}"
        )

    def _infer_primary_language(self, analysis: AnalysisResult, repository_language: Optional[str]) -> str:
        if repository_language:
            return repository_language.strip().lower()
        if analysis.languages_detected:
            return analysis.languages_detected[0].lower()
        return "unknown"

    def _ensure_generated_tests(
        self,
        result: AIReviewResult,
        analysis: AnalysisResult,
        repository_language: Optional[str],
    ) -> AIReviewResult:
        if result.generated_tests and result.generated_tests.strip():
            return result

        language = self._infer_primary_language(analysis, repository_language)
        function_name = "behavior_regression_guard"
        for file_change in analysis.files:
            if file_change.functions_changed:
                function_name = file_change.functions_changed[0]
                break

        result.generated_tests = self._build_test_template(language, function_name)
        return result

    def _build_test_template(self, language: str, function_name: str) -> str:
        safe_name = (function_name or "behavior_regression_guard").replace("-", "_")
        templates = {
            "python": (
                "```python\n"
                f"def test_{safe_name}_regression_guard():\n"
                "    # Arrange\n"
                "    # Act\n"
                "    # Assert\n"
                "    assert True\n"
                "```"
            ),
            "typescript": (
                "```typescript\n"
                f"describe('{safe_name}', () => {{\n"
                "  it('guards existing behavior', () => {\n"
                "    expect(true).toBe(true)\n"
                "  })\n"
                "})\n"
                "```"
            ),
            "javascript": (
                "```javascript\n"
                f"describe('{safe_name}', () => {{\n"
                "  it('guards existing behavior', () => {\n"
                "    expect(true).toBe(true)\n"
                "  })\n"
                "})\n"
                "```"
            ),
            "java": (
                "```java\n"
                "import static org.junit.jupiter.api.Assertions.assertTrue;\n"
                "import org.junit.jupiter.api.Test;\n\n"
                "class RegressionTest {\n"
                "    @Test\n"
                f"    void {safe_name}ShouldPreserveBehavior() {{\n"
                "        assertTrue(true);\n"
                "    }\n"
                "}\n"
                "```"
            ),
            "csharp": (
                "```csharp\n"
                "using Xunit;\n\n"
                "public class RegressionTests\n"
                "{\n"
                "    [Fact]\n"
                f"    public void {safe_name}_PreservesBehavior()\n"
                "    {\n"
                "        Assert.True(true);\n"
                "    }\n"
                "}\n"
                "```"
            ),
            "go": (
                "```go\n"
                "package regression\n\n"
                "import \"testing\"\n\n"
                f"func Test{safe_name.title().replace('_', '')}BehaviorGuard(t *testing.T) {{\n"
                "}\n"
                "```"
            ),
            "ruby": (
                "```ruby\n"
                "RSpec.describe 'regression guard' do\n"
                f"  it 'preserves {safe_name} behavior' do\n"
                "    expect(true).to eq(true)\n"
                "  end\n"
                "end\n"
                "```"
            ),
        }

        return templates.get(
            language,
            "```text\n# Add project-specific regression tests for changed functions and edge cases.\n```",
        )

    async def _call_openai(self, user_content: str) -> str:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
            max_tokens=4096,
        )
        return response.choices[0].message.content or ""

    async def _call_anthropic(self, user_content: str) -> str:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        message = await client.messages.create(
            model="claude-opus-4-5",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        return message.content[0].text

    def _parse_response(self, raw: str, provider: str) -> AIReviewResult:
        try:
            # Strip any accidental markdown fences
            clean = raw.strip()
            if clean.startswith("```"):
                clean = re.sub(r"^```[a-z]*\n?", "", clean)
                clean = re.sub(r"\n?```$", "", clean)
            data = json.loads(clean)
        except Exception as exc:
            log.error("Failed to parse AI response", error=str(exc), raw=raw[:500])
            return self._stub_result()

        comments = [
            AIComment(
                file_path=c.get("file_path", ""),
                line_start=c.get("line_start"),
                line_end=c.get("line_end"),
                category=c.get("category", "best_practice"),
                severity=c.get("severity", "info"),
                body=c.get("body", ""),
                suggested_fix=c.get("suggested_fix"),
                suggested_diff=c.get("suggested_diff"),
            )
            for c in data.get("comments", [])
        ]
        return AIReviewResult(
            quality_score=float(data.get("quality_score", 5.0)),
            summary=data.get("summary", ""),
            generated_docs=data.get("generated_docs", ""),
            generated_tests=data.get("generated_tests", ""),
            comments=comments,
            provider=provider,
        )

    def _stub_result(self) -> AIReviewResult:
        return AIReviewResult(
            quality_score=5.0,
            summary="AI review unavailable — no provider configured.",
            generated_docs="",
            generated_tests="",
            comments=[],
            provider="none",
        )


