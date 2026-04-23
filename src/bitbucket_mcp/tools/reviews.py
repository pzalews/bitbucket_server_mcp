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


async def get_diff(
    ctx: Context,
    project: str | None = None,
    repository: str = "",
    pr_id: int = 0,
    context_lines: int = 10,
    max_lines_per_file: int | None = None,
) -> dict[str, Any]:
    """Get the unified diff for a pull request with optional per-file line truncation.

    context_lines: Number of unchanged context lines around each change (default: 10).
    max_lines_per_file: Truncate each file's hunks after this many lines.
                        Defaults to BITBUCKET_DIFF_MAX_LINES_PER_FILE env var (500).
    """
    project_key = _resolve_project(ctx, project)
    async with log_tool_call("get_diff", project=project_key, repo=repository):
        client: BitbucketClient = ctx.lifespan_context["client"]
        settings: Settings = ctx.lifespan_context["settings"]
        effective_max = max_lines_per_file or settings.bitbucket_diff_max_lines_per_file
        diff = await client.get_pull_request_diff(project_key, repository, pr_id, context_lines)

        for diff_file in diff.get("diffs", []):
            total = 0
            kept_hunks = []
            for hunk in diff_file.get("hunks", []):
                line_count = sum(
                    len(seg.get("lines", [])) for seg in hunk.get("segments", [])
                )
                if total + line_count > effective_max:
                    diff_file["truncated"] = True
                    break
                kept_hunks.append(hunk)
                total += line_count
            diff_file["hunks"] = kept_hunks

        return diff


async def get_activities(
    ctx: Context,
    project: str | None = None,
    repository: str = "",
    pr_id: int = 0,
) -> list[dict[str, Any]]:
    """Get the activity stream for a pull request (comments, approvals, merges, etc.)."""
    project_key = _resolve_project(ctx, project)
    async with log_tool_call("get_activities", project=project_key, repo=repository):
        client: BitbucketClient = ctx.lifespan_context["client"]
        return await client.get_pull_request_activities(project_key, repository, pr_id)


async def get_reviews(
    ctx: Context,
    project: str | None = None,
    repository: str = "",
    pr_id: int = 0,
) -> list[dict[str, Any]]:
    """Get the list of reviewers and their approval status for a pull request."""
    project_key = _resolve_project(ctx, project)
    async with log_tool_call("get_reviews", project=project_key, repo=repository):
        client: BitbucketClient = ctx.lifespan_context["client"]
        return await client.get_pull_request_participants(project_key, repository, pr_id)
