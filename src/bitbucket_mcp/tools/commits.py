from __future__ import annotations

from typing import Any

from fastmcp import Context

from ..client import BitbucketClient
from ..config import Settings
from ..logging_setup import log_tool_call


def _resolve_project(ctx: Context, project: str | None) -> str:
    settings: Settings = ctx.lifespan_context["settings"]
    resolved = project or settings.bitbucket_default_project
    if not resolved:
        raise ValueError("project is required when BITBUCKET_DEFAULT_PROJECT is not set")
    return resolved


async def list_commits(
    ctx: Context,
    project: str | None = None,
    repository: str = "",
    branch: str | None = None,
    author: str | None = None,
    path: str | None = None,
) -> list[dict[str, Any]]:
    """List commits in a repository.

    branch: Branch name or commit SHA to list commits up to.
    author: Filter by author username.
    path: Filter to commits that touched this path.
    """
    project_key = _resolve_project(ctx, project)
    async with log_tool_call("list_commits", project=project_key, repo=repository):
        client: BitbucketClient = ctx.lifespan_context["client"]
        return await client.list_commits(project_key, repository, branch, author, path)


async def get_code_insights(
    ctx: Context,
    project: str | None = None,
    repository: str = "",
    commit_id: str = "",
) -> list[dict[str, Any]]:
    """Get code insights reports for a specific commit.

    commit_id: Full 40-character commit SHA.
    """
    project_key = _resolve_project(ctx, project)
    async with log_tool_call("get_code_insights", project=project_key, repo=repository):
        client: BitbucketClient = ctx.lifespan_context["client"]
        return await client.get_code_insights(project_key, repository, commit_id)
