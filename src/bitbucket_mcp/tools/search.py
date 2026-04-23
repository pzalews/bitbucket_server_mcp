from __future__ import annotations

from typing import Any

from fastmcp import Context

from ..client import BitbucketClient
from ..config import Settings
from ..logging_setup import log_tool_call


async def search(
    ctx: Context,
    query: str = "",
    project: str | None = None,
    repository: str | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    """Search for code across Bitbucket projects and repositories.

    Requires the Bitbucket Server Search plugin to be installed and enabled.
    query: Search query string.
    project: Scope search to a specific project key.
    repository: Scope search to a specific repository slug (requires project).
    limit: Maximum number of results to return per entity type.
    """
    settings: Settings = ctx.lifespan_context["settings"]
    project_key = project or settings.bitbucket_default_project
    async with log_tool_call("search", project=project_key):
        client: BitbucketClient = ctx.lifespan_context["client"]
        return await client.search(query, project_key, repository, limit)
