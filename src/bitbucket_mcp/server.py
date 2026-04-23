from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastmcp import FastMCP

from .client import BitbucketClient
from .config import Settings
from .logging_setup import configure_logging, get_logger
from .prompts import register_prompts
from .resources import register_resources
from .tools import register_all_tools

log = get_logger(__name__)


@asynccontextmanager
async def _lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    settings = Settings()
    configure_logging(
        log_path=settings.bitbucket_log_path,
        json_logs=bool(settings.bitbucket_log_path),
    )
    client = BitbucketClient(settings)
    log.info("bitbucket_mcp.startup", **settings.redacted())
    try:
        yield {"client": client, "settings": settings}
    finally:
        await client.aclose()
        log.info("bitbucket_mcp.shutdown")


def create_server() -> FastMCP:
    mcp = FastMCP(
        name="Bitbucket Server MCP",
        instructions=(
            "Tools for interacting with a self-hosted Bitbucket Server. "
            "Start with list_projects to discover available projects, "
            "then list_repositories to find repos. "
            "For pull requests: list_pull_requests → get_pull_request → get_diff. "
            "Use get_dashboard_pull_requests to see PRs assigned to you across all projects."
        ),
        lifespan=_lifespan,
    )
    register_all_tools(mcp)
    register_resources(mcp)
    register_prompts(mcp)
    return mcp


mcp = create_server()
