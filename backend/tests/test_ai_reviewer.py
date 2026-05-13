"""
Tests for the AI reviewer response parser (no real API calls).
"""
import pytest
import json
from unittest.mock import AsyncMock, patch
from app.ai.reviewer import AIReviewer
from app.analysis.engine import AnalysisResult


MOCK_RESPONSE = json.dumps({
    "quality_score": 7.5,
    "summary": "Overall good code. One security concern.",
    "generated_docs": "## compute_hash\nReturns SHA-256 digest.",
    "comments": [
        {
            "file_path": "app/utils.py",
            "line_start": 12,
            "line_end": 13,
            "category": "security",
            "severity": "critical",
            "body": "Use of eval() is dangerous.",
            "suggested_fix": "# Remove eval or use ast.literal_eval",
            "suggested_diff": None,
        }
    ],
})


@pytest.mark.asyncio
async def test_review_parses_openai_response():
    reviewer = AIReviewer()
    with patch.object(reviewer, "_call_openai", new=AsyncMock(return_value=MOCK_RESPONSE)):
        with patch("app.ai.reviewer.settings") as mock_settings:
            mock_settings.DEFAULT_AI_PROVIDER = "openai"
            mock_settings.OPENAI_API_KEY = "fake-key"
            mock_settings.ANTHROPIC_API_KEY = ""
            result = await reviewer.review("diff --git ...", AnalysisResult())

    assert result.quality_score == 7.5
    assert len(result.comments) == 1
    assert result.comments[0].severity == "critical"
    assert result.comments[0].category == "security"


@pytest.mark.asyncio
async def test_review_stub_when_no_provider():
    reviewer = AIReviewer()
    with patch("app.ai.reviewer.settings") as mock_settings:
        mock_settings.DEFAULT_AI_PROVIDER = "openai"
        mock_settings.OPENAI_API_KEY = ""
        mock_settings.ANTHROPIC_API_KEY = ""
        result = await reviewer.review("diff", AnalysisResult())

    assert result.quality_score == 5.0
    assert result.comments == []
