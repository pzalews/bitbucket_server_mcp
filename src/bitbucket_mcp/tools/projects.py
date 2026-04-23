from __future__ import annotations

from typing import Any

from fastmcp import Context

from ..client import BitbucketClient
from ..logging_setup import log_tool_call


async def list_projects(ctx: Context) -> list[dict[str, Any]]:
    """List all Bitbucket projects accessible to the authenticated user."""
    async with log_tool_call("list_projects"):
        client: BitbucketClient = ctx.lifespan_context["client"]
        return await client.list_projects()
