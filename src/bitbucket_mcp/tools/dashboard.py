from __future__ import annotations

from typing import Any, Literal

from fastmcp import Context

from ..client import BitbucketClient
from ..logging_setup import log_tool_call


async def get_dashboard_pull_requests(
    ctx: Context,
    role: Literal["AUTHOR", "REVIEWER", "PARTICIPANT"] | None = None,
    state: Literal["OPEN", "MERGED", "DECLINED"] | None = None,
    participant_status: Literal["APPROVED", "UNAPPROVED", "NEEDS_WORK"] | None = None,
    order: Literal[
        "NEWEST", "OLDEST", "PARTICIPANT_STATUS", "CLOSED_DATE", "NEWEST_ACTIVITY"
    ] | None = None,
    closed_since: int | None = None,
) -> list[dict[str, Any]]:
    """Get pull requests from the authenticated user's dashboard across all projects.

    role: AUTHOR | REVIEWER | PARTICIPANT
    state: OPEN | MERGED | DECLINED (omit for all states)
    participant_status: APPROVED | UNAPPROVED | NEEDS_WORK
    order: NEWEST | OLDEST | PARTICIPANT_STATUS | CLOSED_DATE | NEWEST_ACTIVITY
    closed_since: Unix timestamp (ms) — only return PRs closed after this time.
    """
    async with log_tool_call("get_dashboard_pull_requests"):
        client: BitbucketClient = ctx.lifespan_context["client"]
        return await client.get_dashboard_pull_requests(
            role, state, participant_status, order, closed_since
        )
