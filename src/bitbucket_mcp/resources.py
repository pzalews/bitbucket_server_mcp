from __future__ import annotations

import json
from typing import Any

from fastmcp import Context, FastMCP


def register_resources(mcp: FastMCP) -> None:

    @mcp.resource("bitbucket://config/effective")
    async def get_effective_config(ctx: Context) -> str:
        """Sanitized server configuration (no secrets)."""
        settings = ctx.lifespan_context["settings"]
        return json.dumps(settings.redacted(), indent=2)

    @mcp.resource("bitbucket://projects")
    async def get_projects_summary(ctx: Context) -> str:
        """Summary of all accessible Bitbucket projects."""
        client = ctx.lifespan_context["client"]
        projects: list[dict[str, Any]] = await client.list_projects()
        summary = [
            {"key": p.get("key"), "name": p.get("name"), "type": p.get("type")}
            for p in projects
        ]
        return json.dumps(summary, indent=2)

    @mcp.resource("bitbucket://repos/{project}")
    async def get_repos_for_project(project: str, ctx: Context) -> str:
        """Summary of repositories in a project."""
        client = ctx.lifespan_context["client"]
        repos: list[dict[str, Any]] = await client.list_repositories(project)
        summary = [
            {"slug": r.get("slug"), "name": r.get("name"), "state": r.get("state")}
            for r in repos
        ]
        return json.dumps(summary, indent=2)

    @mcp.resource("bitbucket://pull-request/{project}/{repo}/{pr_id}")
    async def get_pull_request_resource(
        project: str, repo: str, pr_id: str, ctx: Context
    ) -> str:
        """Compact view of a specific pull request."""
        client = ctx.lifespan_context["client"]
        pr: dict[str, Any] = await client.get_pull_request(project, repo, int(pr_id))
        compact = {
            "id": pr.get("id"),
            "title": pr.get("title"),
            "state": pr.get("state"),
            "author": pr.get("author", {}).get("user", {}).get("displayName"),
            "fromRef": pr.get("fromRef", {}).get("displayId"),
            "toRef": pr.get("toRef", {}).get("displayId"),
            "reviewers": [
                {"name": r.get("user", {}).get("displayName"), "status": r.get("status")}
                for r in pr.get("reviewers", [])
            ],
        }
        return json.dumps(compact, indent=2)
