from __future__ import annotations

from typing import Any, Literal

from fastmcp import Context

from ..client import BitbucketClient
from ..config import Settings
from ..exceptions import ReadOnlyModeError
from ..logging_setup import log_tool_call

_VALID_MERGE_STRATEGIES = {"merge-commit", "squash", "fast-forward"}


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


async def list_pull_requests(
    ctx: Context,
    project: str | None = None,
    repository: str = "",
    state: Literal["OPEN", "MERGED", "DECLINED"] = "OPEN",
    author: str | None = None,
    direction: Literal["INCOMING", "OUTGOING"] | None = None,
) -> list[dict[str, Any]]:
    """List pull requests in a repository.

    state: OPEN | MERGED | DECLINED (default: OPEN)
    direction: INCOMING | OUTGOING
    author: Filter by author username.
    """
    project_key = _resolve_project(ctx, project)
    async with log_tool_call("list_pull_requests", project=project_key, repo=repository):
        client: BitbucketClient = ctx.lifespan_context["client"]
        return await client.list_pull_requests(project_key, repository, state, author, direction)


async def get_pull_request(
    ctx: Context,
    project: str | None = None,
    repository: str = "",
    pr_id: int = 0,
) -> dict[str, Any]:
    """Get detailed information about a specific pull request."""
    project_key = _resolve_project(ctx, project)
    async with log_tool_call("get_pull_request", project=project_key, repo=repository):
        client: BitbucketClient = ctx.lifespan_context["client"]
        return await client.get_pull_request(project_key, repository, pr_id)


async def create_pull_request(
    ctx: Context,
    project: str | None = None,
    repository: str = "",
    title: str = "",
    description: str = "",
    source_branch: str = "",
    target_branch: str = "",
    source_project: str | None = None,
    source_repository: str | None = None,
    reviewers: list[str] | None = None,
    include_default_reviewers: bool = True,
) -> dict[str, Any]:
    """Create a new pull request.

    source_project: Project key of the source repo (defaults to same project).
    source_repository: Slug of the source repo (defaults to same repo, for cross-repo PRs).
    reviewers: List of reviewer usernames to add.
    include_default_reviewers: Fetch and include the repository's default reviewers.
    """
    _require_write(ctx, "create_pull_request")
    project_key = _resolve_project(ctx, project)
    async with log_tool_call("create_pull_request", project=project_key, repo=repository):
        client: BitbucketClient = ctx.lifespan_context["client"]
        all_reviewers = list(reviewers or [])
        if include_default_reviewers:
            try:
                defaults = await client.get_default_reviewers(
                    project_key, repository, source_branch, target_branch
                )
                for r in defaults:
                    name = r.get("name") or r.get("slug")
                    if name and name not in all_reviewers:
                        all_reviewers.append(name)
            except Exception:
                pass  # Default reviewers endpoint may not be available
        return await client.create_pull_request(
            project_key,
            repository,
            title,
            description,
            source_branch,
            target_branch,
            source_project=source_project,
            source_repository=source_repository,
            reviewers=all_reviewers,
        )


async def update_pull_request(
    ctx: Context,
    project: str | None = None,
    repository: str = "",
    pr_id: int = 0,
    title: str | None = None,
    description: str | None = None,
    reviewers: list[str] | None = None,
) -> dict[str, Any]:
    """Update a pull request's title, description, or reviewer list.

    Automatically fetches the current version for optimistic locking.
    """
    _require_write(ctx, "update_pull_request")
    project_key = _resolve_project(ctx, project)
    async with log_tool_call("update_pull_request", project=project_key, repo=repository):
        client: BitbucketClient = ctx.lifespan_context["client"]
        current = await client.get_pull_request(project_key, repository, pr_id)
        updates: dict[str, Any] = {"version": current["version"]}
        updates["title"] = title if title is not None else current.get("title", "")
        updates["description"] = (
            description if description is not None else current.get("description", "")
        )
        if reviewers is not None:
            updates["reviewers"] = [{"user": {"name": r}} for r in reviewers]
        else:
            updates["reviewers"] = current.get("reviewers", [])
        return await client.update_pull_request(project_key, repository, pr_id, updates)


async def merge_pull_request(
    ctx: Context,
    project: str | None = None,
    repository: str = "",
    pr_id: int = 0,
    strategy: str = "merge-commit",
) -> dict[str, Any]:
    """Merge a pull request. Fetches the current version automatically.

    strategy: merge-commit | squash | fast-forward (default: merge-commit)
    """
    _require_write(ctx, "merge_pull_request")
    if strategy not in _VALID_MERGE_STRATEGIES:
        raise ValueError(
            f"Invalid strategy '{strategy}'. Choose from: {sorted(_VALID_MERGE_STRATEGIES)}"
        )
    project_key = _resolve_project(ctx, project)
    async with log_tool_call("merge_pull_request", project=project_key, repo=repository):
        client: BitbucketClient = ctx.lifespan_context["client"]
        pr = await client.get_pull_request(project_key, repository, pr_id)
        return await client.merge_pull_request(
            project_key, repository, pr_id, pr["version"], strategy
        )


async def decline_pull_request(
    ctx: Context,
    project: str | None = None,
    repository: str = "",
    pr_id: int = 0,
) -> dict[str, Any]:
    """Decline a pull request. Fetches the current version automatically."""
    _require_write(ctx, "decline_pull_request")
    project_key = _resolve_project(ctx, project)
    async with log_tool_call("decline_pull_request", project=project_key, repo=repository):
        client: BitbucketClient = ctx.lifespan_context["client"]
        pr = await client.get_pull_request(project_key, repository, pr_id)
        return await client.decline_pull_request(project_key, repository, pr_id, pr["version"])


async def approve_pull_request(
    ctx: Context,
    project: str | None = None,
    repository: str = "",
    pr_id: int = 0,
) -> dict[str, Any]:
    """Approve a pull request as the authenticated user."""
    _require_write(ctx, "approve_pull_request")
    project_key = _resolve_project(ctx, project)
    async with log_tool_call("approve_pull_request", project=project_key, repo=repository):
        client: BitbucketClient = ctx.lifespan_context["client"]
        return await client.approve_pull_request(project_key, repository, pr_id)


async def unapprove_pull_request(
    ctx: Context,
    project: str | None = None,
    repository: str = "",
    pr_id: int = 0,
) -> dict[str, str]:
    """Remove approval from a pull request."""
    _require_write(ctx, "unapprove_pull_request")
    project_key = _resolve_project(ctx, project)
    async with log_tool_call("unapprove_pull_request", project=project_key, repo=repository):
        client: BitbucketClient = ctx.lifespan_context["client"]
        await client.unapprove_pull_request(project_key, repository, pr_id)
        return {"status": "unapproved", "pr_id": str(pr_id)}
