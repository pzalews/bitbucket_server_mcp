from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bitbucket_mcp.exceptions import ReadOnlyModeError
from bitbucket_mcp.tools.pull_requests import (
    approve_pull_request,
    create_pull_request,
    list_pull_requests,
    merge_pull_request,
)


def _make_ctx(client: AsyncMock, read_only: bool = False) -> MagicMock:
    settings = MagicMock()
    settings.bitbucket_read_only = read_only
    settings.bitbucket_default_project = "PROJ"
    ctx = MagicMock()
    ctx.lifespan_context = {"client": client, "settings": settings}
    return ctx


@pytest.mark.asyncio
async def test_list_pull_requests_calls_client() -> None:
    client = AsyncMock()
    client.list_pull_requests.return_value = [{"id": 1, "title": "Test PR"}]
    ctx = _make_ctx(client)
    result = await list_pull_requests(ctx=ctx, repository="repo", state="OPEN")
    client.list_pull_requests.assert_called_once_with("PROJ", "repo", "OPEN", None, None)
    assert result[0]["id"] == 1


@pytest.mark.asyncio
async def test_merge_pr_fetches_version() -> None:
    client = AsyncMock()
    client.get_pull_request.return_value = {"id": 1, "version": 5, "state": "OPEN"}
    client.merge_pull_request.return_value = {"id": 1, "state": "MERGED"}
    ctx = _make_ctx(client)
    result = await merge_pull_request(ctx=ctx, repository="repo", pr_id=1)
    client.merge_pull_request.assert_called_once_with("PROJ", "repo", 1, 5, "merge-commit")
    assert result["state"] == "MERGED"


@pytest.mark.asyncio
async def test_merge_pr_invalid_strategy() -> None:
    ctx = _make_ctx(AsyncMock())
    with pytest.raises(ValueError, match="Invalid strategy"):
        await merge_pull_request(ctx=ctx, repository="repo", pr_id=1, strategy="rebase")


@pytest.mark.asyncio
async def test_create_pr_read_only_blocked() -> None:
    ctx = _make_ctx(AsyncMock(), read_only=True)
    with pytest.raises(ReadOnlyModeError):
        await create_pull_request(
            ctx=ctx, repository="repo", title="T", description="D",
            source_branch="feat", target_branch="main",
        )


@pytest.mark.asyncio
async def test_approve_pr_read_only_blocked() -> None:
    ctx = _make_ctx(AsyncMock(), read_only=True)
    with pytest.raises(ReadOnlyModeError):
        await approve_pull_request(ctx=ctx, repository="repo", pr_id=1)
