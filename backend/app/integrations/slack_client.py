"""
Slack integration — sends notifications for critical issues found in reviews.
"""
import structlog
import httpx
from typing import List

from app.core.config import settings

log = structlog.get_logger()

SLACK_API = "https://slack.com/api/chat.postMessage"


class SlackClient:
    async def notify_critical_issues(
        self,
        repo: str,
        pr_number: int,
        pr_url: str,
        issues: List,
    ):
        if not settings.SLACK_BOT_TOKEN or not settings.SLACK_CHANNEL_ID:
            log.debug("Slack not configured, skipping notification")
            return

        critical_count = sum(1 for i in issues if i.severity == "critical")
        high_count = sum(1 for i in issues if i.severity == "high")

        issue_lines = []
        for issue in issues[:5]:  # cap at 5 in the notification
            issue_lines.append(f"• *{issue.severity.upper()}* `{issue.file_path}`: {issue.body[:120]}")

        text = (
            f":rotating_light: *AI Code Review Alert* — <{pr_url}|{repo}#{pr_number}>\n"
            f"Found *{critical_count} critical* and *{high_count} high* severity issues.\n\n"
            + "\n".join(issue_lines)
        )

        payload = {
            "channel": settings.SLACK_CHANNEL_ID,
            "text": text,
            "unfurl_links": False,
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    SLACK_API,
                    headers={"Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}"},
                    json=payload,
                    timeout=10,
                )
                data = resp.json()
                if not data.get("ok"):
                    log.error("Slack API error", error=data.get("error"))
        except Exception as exc:
            log.warning("Slack notification failed", error=str(exc))
