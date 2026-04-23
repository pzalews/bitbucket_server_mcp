from __future__ import annotations

import re
from typing import Any

from fastmcp import Context

from ..client import BitbucketClient
from ..config import Settings
from ..exceptions import ConflictError, DefaultBranchProtectionError, ReadOnlyModeError
from ..logging_setup import log_tool_call

_VALID_BRANCH = re.compile(r"^[a-zA-Z0-9._/\-]+$")


def _require_write(ctx: Context, tool_name: str) -> None:
    settings: Settings = ctx.lifespan_context["settings"]
    if settings.bitbucket_read_only:
        raise ReadOnlyModeError(tool_name)


def _resolve_project(ctx: Context, project: str | None) -> str:
    settings: Settings = ctx.lifespan_context["settings"]
    resolved = project or settings.bitbucket_default_project
    if not resolved:
        raise ValueError("project is required when BITBUCKET_DEFAULT_PROJECT is not set")
    return resolved


async def list_branches(
    ctx: Context,
    project: str | None = None,
    repository: str = "",
    filter_text: str | None = None,
) -> list[dict[str, Any]]:
    """List branches in a repository with optional name filter.

    filter_text: Partial branch name to filter by (case-insensitive prefix match).
    """
    project_key = _resolve_project(ctx, project)
    async with log_tool_call("list_branches", project=project_key, repo=repository):
        client: BitbucketClient = ctx.lifespan_context["client"]
        return await client.list_branches(project_key, repository, filter_text)


async def create_branch(
    ctx: Context,
    project: str | None = None,
    repository: str = "",
    name: str = "",
    start_point: str = "",
) -> dict[str, Any]:
    """Create a new branch from a branch name or commit SHA.

    name: New branch name (e.g. 'feature/my-feature').
    start_point: Source branch name or 40-char commit SHA.
    """
    _require_write(ctx, "create_branch")
    project_key = _resolve_project(ctx, project)

    display_name = name.removeprefix("refs/heads/")
    if not _VALID_BRANCH.match(display_name):
        raise ValueError(
            f"Invalid branch name '{display_name}'. "
            "Use only alphanumerics, dots, hyphens, underscores, and slashes."
        )

    async with log_tool_call("create_branch", project=project_key, repo=repository):
        client: BitbucketClient = ctx.lifespan_context["client"]
        existing = await client.list_branches(project_key, repository, filter_text=display_name)
        for b in existing:
            if b.get("displayId") == display_name:
                raise ConflictError(409, f"Branch '{display_name}' already exists")
        return await client.create_branch(project_key, repository, name, start_point)


async def delete_branch(
    ctx: Context,
    project: str | None = None,
    repository: str = "",
    name: str = "",
) -> dict[str, str]:
    """Delete a branch. Refuses to delete the repository's default branch.

    name: Branch name to delete (e.g. 'feature/my-feature').
    """
    _require_write(ctx, "delete_branch")
    project_key = _resolve_project(ctx, project)

    async with log_tool_call("delete_branch", project=project_key, repo=repository):
        client: BitbucketClient = ctx.lifespan_context["client"]
        default = await client.get_default_branch(project_key, repository)
        default_display = default.get("displayId", "")
        display_name = name.removeprefix("refs/heads/")
        if display_name == default_display or name == default.get("id", ""):
            raise DefaultBranchProtectionError(
                f"Cannot delete default branch '{default_display}'. "
                "Change the repository's default branch first."
            )
        await client.delete_branch(project_key, repository, name)
        return {"deleted": display_name, "project": project_key, "repository": repository}
