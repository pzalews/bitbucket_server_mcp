from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bitbucket_mcp.exceptions import ReadOnlyModeError
from bitbucket_mcp.tools.comments import (
    add_comment,
    delete_comment,
    edit_comment,
    publish_review,
)


def _make_ctx(client: AsyncMock, read_only: bool = False) -> MagicMock:
    settings = MagicMock()
    settings.bitbucket_read_only = read_only
    settings.bitbucket_default_project = "PROJ"
    ctx = MagicMock()
    ctx.lifespan_context = {"client": client, "settings": settings}
    return ctx


@pytest.mark.asyncio
async def test_add_comment_read_only() -> None:
    ctx = _make_ctx(AsyncMock(), read_only=True)
    with pytest.raises(ReadOnlyModeError):
        await add_comment(ctx=ctx, repository="r", pr_id=1, text="hello")


@pytest.mark.asyncio
async def test_edit_comment_auto_fetches_version() -> None:
    client = AsyncMock()
    client.get_comment.return_value = {"id": 5, "version": 3, "text": "old"}
    client.edit_comment.return_value = {"id": 5, "version": 4, "text": "new"}
    ctx = _make_ctx(client)
    await edit_comment(ctx=ctx, repository="repo", pr_id=1, comment_id=5, text="new")
    client.edit_comment.assert_called_once_with("PROJ", "repo", 1, 5, "new", 3)


@pytest.mark.asyncio
async def test_delete_comment_auto_fetches_version() -> None:
    client = AsyncMock()
    client.get_comment.return_value = {"id": 5, "version": 2}
    ctx = _make_ctx(client)
    await delete_comment(ctx=ctx, repository="repo", pr_id=1, comment_id=5)
    client.delete_comment.assert_called_once_with("PROJ", "repo", 1, 5, 2)


@pytest.mark.asyncio
async def test_publish_review_with_comment_and_status() -> None:
    client = AsyncMock()
    client.add_comment.return_value = {"id": 10}
    client.get_pull_request_participants.return_value = [
        {"role": "REVIEWER", "user": {"slug": "jdoe"}}
    ]
    client.update_participant_status.return_value = {"status": "APPROVED"}
    ctx = _make_ctx(client)
    result = await publish_review(
        ctx=ctx, repository="repo", pr_id=1, overall_comment="LGTM", status="APPROVED"
    )
    assert result["comment"] == {"id": 10}
    client.update_participant_status.assert_called_once_with("PROJ", "repo", 1, "jdoe", "APPROVED")


@pytest.mark.asyncio
async def test_publish_review_invalid_status() -> None:
    ctx = _make_ctx(AsyncMock())
    with pytest.raises(ValueError, match="status must be"):
        await publish_review(ctx=ctx, repository="r", pr_id=1, status="UNKNOWN")
