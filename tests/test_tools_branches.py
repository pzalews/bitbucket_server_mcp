from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bitbucket_mcp.exceptions import (
    ConflictError,
    DefaultBranchProtectionError,
    ReadOnlyModeError,
)
from bitbucket_mcp.tools.branches import create_branch, delete_branch, list_branches


def _make_ctx(
    client: AsyncMock,
    read_only: bool = False,
    default_project: str | None = None,
) -> MagicMock:
    settings = MagicMock()
    settings.bitbucket_read_only = read_only
    settings.bitbucket_default_project = default_project
    ctx = MagicMock()
    ctx.lifespan_context = {"client": client, "settings": settings}
    return ctx


@pytest.mark.asyncio
async def test_list_branches_calls_client() -> None:
    client = AsyncMock()
    client.list_branches.return_value = [{"displayId": "main"}]
    ctx = _make_ctx(client, default_project="PROJ")
    result = await list_branches(ctx=ctx, repository="repo")
    client.list_branches.assert_called_once_with("PROJ", "repo", None)
    assert result == [{"displayId": "main"}]


@pytest.mark.asyncio
async def test_delete_branch_blocks_default() -> None:
    client = AsyncMock()
    client.get_default_branch.return_value = {"displayId": "main", "id": "refs/heads/main"}
    ctx = _make_ctx(client, default_project="PROJ")
    with pytest.raises(DefaultBranchProtectionError):
        await delete_branch(ctx=ctx, repository="repo", name="main")


@pytest.mark.asyncio
async def test_delete_branch_read_only() -> None:
    ctx = _make_ctx(AsyncMock(), read_only=True, default_project="P")
    with pytest.raises(ReadOnlyModeError) as exc_info:
        await delete_branch(ctx=ctx, repository="repo", name="feature/x")
    assert "delete_branch" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_branch_read_only() -> None:
    ctx = _make_ctx(AsyncMock(), read_only=True, default_project="P")
    with pytest.raises(ReadOnlyModeError):
        await create_branch(ctx=ctx, repository="r", name="feat", start_point="main")


@pytest.mark.asyncio
async def test_create_branch_invalid_name() -> None:
    ctx = _make_ctx(AsyncMock(), default_project="P")
    with pytest.raises(ValueError, match="Invalid branch name"):
        await create_branch(ctx=ctx, repository="r", name="feat!!!", start_point="main")


@pytest.mark.asyncio
async def test_create_branch_already_exists() -> None:
    client = AsyncMock()
    client.list_branches.return_value = [{"displayId": "feature/x"}]
    ctx = _make_ctx(client, default_project="PROJ")
    with pytest.raises(ConflictError):
        await create_branch(ctx=ctx, repository="repo", name="feature/x", start_point="main")


@pytest.mark.asyncio
async def test_create_branch_success() -> None:
    client = AsyncMock()
    client.list_branches.return_value = []
    client.create_branch.return_value = {"displayId": "feature/new", "id": "refs/heads/feature/new"}
    ctx = _make_ctx(client, default_project="PROJ")
    result = await create_branch(ctx=ctx, repository="repo", name="feature/new", start_point="main")
    client.create_branch.assert_called_once_with("PROJ", "repo", "feature/new", "main")
    assert result["displayId"] == "feature/new"
