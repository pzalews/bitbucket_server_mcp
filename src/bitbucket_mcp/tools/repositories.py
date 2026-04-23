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
        raise ValueError(
            "project is required when BITBUCKET_DEFAULT_PROJECT is not set"
        )
    return resolved


async def list_repositories(
    ctx: Context,
    project: str | None = None,
) -> list[dict[str, Any]]:
    """List all repositories in a Bitbucket project.

    project: Project key (e.g. 'MYPROJ'). Falls back to BITBUCKET_DEFAULT_PROJECT.
    """
    project_key = _resolve_project(ctx, project)
    async with log_tool_call("list_repositories", project=project_key):
        client: BitbucketClient = ctx.lifespan_context["client"]
        return await client.list_repositories(project_key)


async def browse_repository(
    ctx: Context,
    project: str | None = None,
    repository: str = "",
    path: str = "",
    at: str | None = None,
) -> dict[str, Any]:
    """Browse the file tree of a repository at a given path.

    path: Directory or file path within the repo (empty = root).
    at: Branch name or commit SHA. Defaults to the repo's default branch.
    """
    project_key = _resolve_project(ctx, project)
    async with log_tool_call("browse_repository", project=project_key, repo=repository):
        client: BitbucketClient = ctx.lifespan_context["client"]
        return await client.browse_repository(project_key, repository, path, at)


async def get_file_content(
    ctx: Context,
    project: str | None = None,
    repository: str = "",
    path: str = "",
    at: str | None = None,
) -> str:
    """Get the raw content of a file from a repository.

    path: File path within the repo (e.g. 'src/main/app.py').
    at: Branch name or commit SHA. Defaults to the repo's default branch.
    """
    project_key = _resolve_project(ctx, project)
    async with log_tool_call("get_file_content", project=project_key, repo=repository):
        client: BitbucketClient = ctx.lifespan_context["client"]
        return await client.get_file_content(project_key, repository, path, at)
