"""
Integration-style API tests using httpx TestClient.
Requires DATABASE_URL pointing to a test DB.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_reviews_list():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/reviews/")
    assert resp.status_code == 200
    body = resp.json()
    assert "reviews" in body
    assert "total" in body


@pytest.mark.asyncio
async def test_metrics_summary():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/metrics/summary")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_webhook_rejects_bad_signature():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/webhooks/github",
            json={"action": "opened"},
            headers={"X-Hub-Signature-256": "sha256=bad", "X-Github-Event": "pull_request"},
        )
    assert resp.status_code == 401
