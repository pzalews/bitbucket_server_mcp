from __future__ import annotations

from typing import Any, Literal

from fastmcp import Context

from ..client import BitbucketClient
from ..config import Settings
from ..exceptions import ReadOnlyModeError
from ..logging_setup import log_tool_call


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


async def get_comments(
    ctx: Context,
    project: str | None = None,
    repository: str = "",
    pr_id: int = 0,
) -> list[dict[str, Any]]:
    """Get all comments on a pull request."""
    project_key = _resolve_project(ctx, project)
    async with log_tool_call("get_comments", project=project_key, repo=repository):
        client: BitbucketClient = ctx.lifespan_context["client"]
        return await client.get_pull_request_comments(project_key, repository, pr_id)


async def add_comment(
    ctx: Context,
    project: str | None = None,
    repository: str = "",
    pr_id: int = 0,
    text: str = "",
    state: Literal["OPEN", "PENDING"] = "OPEN",
    parent_id: int | None = None,
) -> dict[str, Any]:
    """Add a comment to a pull request.

    state: OPEN (visible immediately) | PENDING (draft, publish later).
    parent_id: Comment ID to reply to (creates a threaded reply).
    """
    _require_write(ctx, "add_comment")
    project_key = _resolve_project(ctx, project)
    async with log_tool_call("add_comment", project=project_key, repo=repository):
        client: BitbucketClient = ctx.lifespan_context["client"]
        return await client.add_comment(project_key, repository, pr_id, text, state, parent_id)


async def add_comment_inline(
    ctx: Context,
    project: str | None = None,
    repository: str = "",
    pr_id: int = 0,
    text: str = "",
    file_path: str = "",
    line_number: int = 1,
    line_type: str = "ADDED",
    file_type: str = "TO",
) -> dict[str, Any]:
    """Add an inline comment anchored to a specific file and line in a PR diff.

    line_type: ADDED | REMOVED | CONTEXT (which side of the diff the line is on).
    file_type: TO (new file) | FROM (old file).
    """
    _require_write(ctx, "add_comment_inline")
    project_key = _resolve_project(ctx, project)
    async with log_tool_call("add_comment_inline", project=project_key, repo=repository):
        client: BitbucketClient = ctx.lifespan_context["client"]
        return await client.add_comment_inline(
            project_key, repository, pr_id, text, file_path, line_number, line_type, file_type
        )


async def edit_comment(
    ctx: Context,
    project: str | None = None,
    repository: str = "",
    pr_id: int = 0,
    comment_id: int = 0,
    text: str = "",
    version: int | None = None,
) -> dict[str, Any]:
    """Edit an existing comment. Fetches the current version automatically if not provided."""
    _require_write(ctx, "edit_comment")
    project_key = _resolve_project(ctx, project)
    async with log_tool_call("edit_comment", project=project_key, repo=repository):
        client: BitbucketClient = ctx.lifespan_context["client"]
        effective_version = version
        if effective_version is None:
            current = await client.get_comment(project_key, repository, pr_id, comment_id)
            effective_version = current["version"]
        return await client.edit_comment(
            project_key, repository, pr_id, comment_id, text, effective_version
        )


async def delete_comment(
    ctx: Context,
    project: str | None = None,
    repository: str = "",
    pr_id: int = 0,
    comment_id: int = 0,
    version: int | None = None,
) -> dict[str, str]:
    """Delete a comment. Fetches the current version automatically if not provided."""
    _require_write(ctx, "delete_comment")
    project_key = _resolve_project(ctx, project)
    async with log_tool_call("delete_comment", project=project_key, repo=repository):
        client: BitbucketClient = ctx.lifespan_context["client"]
        effective_version = version
        if effective_version is None:
            current = await client.get_comment(project_key, repository, pr_id, comment_id)
            effective_version = current["version"]
        await client.delete_comment(project_key, repository, pr_id, comment_id, effective_version)
        return {"deleted": str(comment_id)}


async def publish_review(
    ctx: Context,
    project: str | None = None,
    repository: str = "",
    pr_id: int = 0,
    overall_comment: str | None = None,
    status: Literal["APPROVED", "UNAPPROVED", "NEEDS_WORK"] = "APPROVED",
    reviewer_slug: str | None = None,
) -> dict[str, Any]:
    """Publish a PR review: post an overall comment and set participant status.

    status: APPROVED | UNAPPROVED | NEEDS_WORK
    reviewer_slug: Your Bitbucket username slug (auto-detected from PR participants if omitted).
    overall_comment: Optional overall review comment to post on the PR.
    """
    _require_write(ctx, "publish_review")
    project_key = _resolve_project(ctx, project)
    async with log_tool_call("publish_review", project=project_key, repo=repository):
        client: BitbucketClient = ctx.lifespan_context["client"]
        results: dict[str, Any] = {}

        if overall_comment:
            results["comment"] = await client.add_comment(
                project_key, repository, pr_id, overall_comment
            )

        slug = reviewer_slug
        if not slug:
            participants = await client.get_pull_request_participants(
                project_key, repository, pr_id
            )
            for p in participants:
                if p.get("role") == "REVIEWER":
                    slug = p.get("user", {}).get("slug")
                    break

        if slug:
            results["participant_status"] = await client.update_participant_status(
                project_key, repository, pr_id, slug, status
            )
        else:
            results["warning"] = (
                "Could not determine reviewer slug. "
                "Pass reviewer_slug explicitly to set participant status."
            )
        return results
