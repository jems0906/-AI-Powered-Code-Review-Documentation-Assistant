"""
GitLab API client — fetches MR diffs/metadata and posts review notes.
"""
import structlog
import httpx
from urllib.parse import quote_plus

from app.core.config import settings

log = structlog.get_logger()


class GitLabClient:
    def __init__(self):
        self.base_url = settings.GITLAB_API_URL.rstrip("/")

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if settings.GITLAB_TOKEN:
            headers["PRIVATE-TOKEN"] = settings.GITLAB_TOKEN
        return headers

    async def get_merge_request(self, project_id: int, mr_iid: int) -> dict:
        project = quote_plus(str(project_id))
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}/projects/{project}/merge_requests/{mr_iid}",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def get_merge_request_diff(self, project_id: int, mr_iid: int) -> str:
        project = quote_plus(str(project_id))
        async with httpx.AsyncClient(timeout=30) as client:
            # The changes endpoint provides unified diffs in each change entry.
            resp = await client.get(
                f"{self.base_url}/projects/{project}/merge_requests/{mr_iid}/changes",
                headers=self._headers(),
            )
            if resp.status_code != 200:
                log.warning("Could not fetch GitLab MR changes", status=resp.status_code)
                return ""

            data = resp.json()
            chunks = []
            for change in data.get("changes", []):
                diff = change.get("diff")
                if diff:
                    chunks.append(diff)
            return "\n".join(chunks)

    async def post_merge_request_note(self, project_id: int, mr_iid: int, body: str):
        if not settings.GITLAB_TOKEN:
            log.info("GitLab posting disabled — no token configured")
            return

        project = quote_plus(str(project_id))
        payload = {"body": body}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/projects/{project}/merge_requests/{mr_iid}/notes",
                headers=self._headers(),
                json=payload,
            )
            if resp.status_code not in (200, 201):
                log.error("Failed to post GitLab note", status=resp.status_code, body=resp.text[:300])
