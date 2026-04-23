from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bitbucket_mcp.exceptions import ReadOnlyModeError
from bitbucket_mcp.tools.branches import create_branch, delete_branch
from bitbucket_mcp.tools.comments import (
    add_comment,
    add_comment_inline,
    delete_comment,
    edit_comment,
    publish_review,
)
from bitbucket_mcp.tools.pull_requests import (
    approve_pull_request,
    create_pull_request,
    decline_pull_request,
    merge_pull_request,
    unapprove_pull_request,
    update_pull_request,
)

WRITE_TOOL_CALLS = [
    (create_branch, dict(repository="r", name="b", start_point="main")),
    (delete_branch, dict(repository="r", name="b")),
    (add_comment, dict(repository="r", pr_id=1, text="hi")),
    (add_comment_inline, dict(repository="r", pr_id=1, text="hi", file_path="f.py", line_number=1)),
    (edit_comment, dict(repository="r", pr_id=1, comment_id=1, text="hi")),
    (delete_comment, dict(repository="r", pr_id=1, comment_id=1)),
    (publish_review, dict(repository="r", pr_id=1)),
    (create_pull_request, dict(repository="r", title="T", description="D",
                               source_branch="s", target_branch="t")),
    (update_pull_request, dict(repository="r", pr_id=1)),
    (merge_pull_request, dict(repository="r", pr_id=1)),
    (decline_pull_request, dict(repository="r", pr_id=1)),
    (approve_pull_request, dict(repository="r", pr_id=1)),
    (unapprove_pull_request, dict(repository="r", pr_id=1)),
]


def _make_read_only_ctx() -> MagicMock:
    settings = MagicMock()
    settings.bitbucket_read_only = True
    settings.bitbucket_default_project = "P"
    ctx = MagicMock()
    ctx.lifespan_context = {"client": AsyncMock(), "settings": settings}
    return ctx


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_fn,kwargs", WRITE_TOOL_CALLS)
async def test_write_tool_blocked_in_read_only(tool_fn, kwargs) -> None:
    ctx = _make_read_only_ctx()
    with pytest.raises(ReadOnlyModeError):
        await tool_fn(ctx=ctx, **kwargs)
