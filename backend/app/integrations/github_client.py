"""
GitHub API client — fetches PR diffs and posts review comments.
"""
import structlog
import httpx
from typing import List, Optional

from app.core.config import settings

log = structlog.get_logger()

GITHUB_API = "https://api.github.com"


class GitHubClient:
    def __init__(self):
        self._token: Optional[str] = None

    async def _get_token(self) -> str:
        """Generate installation access token from GitHub App credentials."""
        if not settings.GITHUB_APP_ID:
            return ""
        # For simplicity, support both App auth and personal access token
        # (PAT can be set as GITHUB_APP_PRIVATE_KEY_PATH = "token:<PAT>")
        key_path = settings.GITHUB_APP_PRIVATE_KEY_PATH
        if key_path.startswith("token:"):
            return key_path[6:]

        try:
            import time
            import jwt as pyjwt
            with open(key_path, "r") as f:
                private_key = f.read()
            now = int(time.time())
            payload = {"iat": now - 60, "exp": now + 600, "iss": settings.GITHUB_APP_ID}
            jwt_token = pyjwt.encode(payload, private_key, algorithm="RS256")

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{GITHUB_API}/app/installations/{settings.GITHUB_INSTALLATION_ID}/access_tokens",
                    headers={"Authorization": f"Bearer {jwt_token}", "Accept": "application/vnd.github+json"},
                )
                resp.raise_for_status()
                return resp.json()["token"]
        except Exception as exc:
            log.warning("Could not obtain GitHub installation token", error=str(exc))
            return ""

    async def _headers(self) -> dict:
        token = await self._get_token()
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def get_pr(self, repo: str, pr_number: int) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{GITHUB_API}/repos/{repo}/pulls/{pr_number}",
                headers=await self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def get_pr_diff(self, repo: str, pr_number: int) -> str:
        headers = await self._headers()
        headers["Accept"] = "application/vnd.github.diff"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{GITHUB_API}/repos/{repo}/pulls/{pr_number}",
                headers=headers,
            )
            if resp.status_code == 200:
                return resp.text
            log.warning("Could not fetch PR diff", status=resp.status_code)
            return ""

    async def post_review(
        self,
        repo_full_name: str,
        pr_number: int,
        head_sha: str,
        summary: str,
        comments: List,
    ):
        if not settings.GITHUB_APP_ID:
            log.info("GitHub posting disabled — no APP_ID configured")
            return

        review_comments = []
        for c in comments:
            if c.file_path and c.line_start:
                review_comments.append({
                    "path": c.file_path,
                    "line": c.line_start,
                    "side": "RIGHT",
                    "body": f"**[{c.severity.upper()}] {c.category}**\n\n{c.body}"
                            + (f"\n\n```suggestion\n{c.suggested_fix}\n```" if c.suggested_fix else ""),
                })

        payload = {
            "commit_id": head_sha,
            "body": summary,
            "event": "COMMENT",
            "comments": review_comments,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{GITHUB_API}/repos/{repo_full_name}/pulls/{pr_number}/reviews",
                headers=await self._headers(),
                json=payload,
            )
            if resp.status_code not in (200, 201):
                log.error("Failed to post GitHub review", status=resp.status_code, body=resp.text[:300])
