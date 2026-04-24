# Literal Enum Types Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all plain `str` enum parameters in tool functions with `Literal` types so that FastMCP exposes correct enum schemas to LLMs, and remove the `ALL` pseudo-value that the Bitbucket Server API rejects.

**Architecture:** All changes are at the tool layer only (`tools/*.py`). `Literal` type annotations cause FastMCP to emit `{"enum": [...]}` in the MCP JSON schema, which LLMs use to select valid values. The manual `valid_statuses` guard in `publish_review` is removed because FastMCP schema enforcement replaces it. Runtime validation for direct Python calls is covered by mypy strict mode (already configured).

**Tech Stack:** Python `typing.Literal`, FastMCP, mypy, pytest, respx

---

## File Map

| File | Change |
|---|---|
| `src/bitbucket_mcp/tools/pull_requests.py` | `state`, `direction` → `Literal` |
| `src/bitbucket_mcp/tools/dashboard.py` | `state`, `role`, `participant_status`, `order` → `Literal` |
| `src/bitbucket_mcp/tools/comments.py` | `state` (add_comment), `status` (publish_review) → `Literal`; remove manual guard |
| `tests/test_server_registration.py` | Add schema enum tests |
| `tests/test_tools_comments.py` | Remove test for deleted manual guard |

---

### Task 1: Add schema enum tests (failing first)

**Files:**
- Modify: `tests/test_server_registration.py`

- [ ] **Step 1: Add failing schema tests**

Append to `tests/test_server_registration.py`:

```python
def test_pull_request_state_enum_schema() -> None:
    mcp = create_server()
    tools = asyncio.run(mcp.list_tools())
    tool = next(t for t in tools if t.name == "list_pull_requests")
    state_schema = tool.inputSchema["properties"]["state"]
    assert set(state_schema["enum"]) == {"OPEN", "MERGED", "DECLINED"}


def test_pull_request_direction_enum_schema() -> None:
    mcp = create_server()
    tools = asyncio.run(mcp.list_tools())
    tool = next(t for t in tools if t.name == "list_pull_requests")
    direction_schema = tool.inputSchema["properties"]["direction"]
    assert set(direction_schema["enum"]) == {"INCOMING", "OUTGOING"}


def test_dashboard_pr_enum_schemas() -> None:
    mcp = create_server()
    tools = asyncio.run(mcp.list_tools())
    tool = next(t for t in tools if t.name == "get_dashboard_pull_requests")
    props = tool.inputSchema["properties"]
    assert set(props["state"]["enum"]) == {"OPEN", "MERGED", "DECLINED"}
    assert set(props["role"]["enum"]) == {"AUTHOR", "REVIEWER", "PARTICIPANT"}
    assert set(props["participant_status"]["enum"]) == {"APPROVED", "UNAPPROVED", "NEEDS_WORK"}
    assert set(props["order"]["enum"]) == {
        "NEWEST", "OLDEST", "PARTICIPANT_STATUS", "CLOSED_DATE", "NEWEST_ACTIVITY"
    }


def test_add_comment_state_enum_schema() -> None:
    mcp = create_server()
    tools = asyncio.run(mcp.list_tools())
    tool = next(t for t in tools if t.name == "add_comment")
    state_schema = tool.inputSchema["properties"]["state"]
    assert set(state_schema["enum"]) == {"OPEN", "PENDING"}


def test_publish_review_status_enum_schema() -> None:
    mcp = create_server()
    tools = asyncio.run(mcp.list_tools())
    tool = next(t for t in tools if t.name == "publish_review")
    status_schema = tool.inputSchema["properties"]["status"]
    assert set(status_schema["enum"]) == {"APPROVED", "UNAPPROVED", "NEEDS_WORK"}
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_server_registration.py -v -k "enum_schema"
```

Expected: All 5 new tests FAIL with `KeyError: 'enum'` (state/direction are plain `str` now, no enum in schema).

---

### Task 2: Update `tools/pull_requests.py`

**Files:**
- Modify: `src/bitbucket_mcp/tools/pull_requests.py`

- [ ] **Step 1: Replace `str` with `Literal` for `state` and `direction`**

Change the import line at the top from:
```python
from typing import Any
```
to:
```python
from typing import Any, Literal
```

Change the `list_pull_requests` signature and docstring from:
```python
async def list_pull_requests(
    ctx: Context,
    project: str | None = None,
    repository: str = "",
    state: str = "OPEN",
    author: str | None = None,
    direction: str | None = None,
) -> list[dict[str, Any]]:
    """List pull requests in a repository.

    state: OPEN | MERGED | DECLINED | ALL (default: OPEN)
    direction: INCOMING | OUTGOING
    author: Filter by author username.
    """
```
to:
```python
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
```

- [ ] **Step 2: Run the enum schema tests for pull_requests**

```bash
python -m pytest tests/test_server_registration.py::test_pull_request_state_enum_schema tests/test_server_registration.py::test_pull_request_direction_enum_schema -v
```

Expected: Both PASS.

- [ ] **Step 3: Run full test suite to check for regressions**

```bash
make check
```

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add src/bitbucket_mcp/tools/pull_requests.py tests/test_server_registration.py
git commit -m "feat: use Literal types for state and direction in list_pull_requests"
```

---

### Task 3: Update `tools/dashboard.py`

**Files:**
- Modify: `src/bitbucket_mcp/tools/dashboard.py`

- [ ] **Step 1: Replace `str` with `Literal` for all 4 parameters**

Change the import line at the top from:
```python
from typing import Any
```
to:
```python
from typing import Any, Literal
```

Replace the entire `get_dashboard_pull_requests` function signature and docstring from:
```python
async def get_dashboard_pull_requests(
    ctx: Context,
    role: str | None = None,
    state: str | None = None,
    participant_status: str | None = None,
    order: str | None = None,
    closed_since: int | None = None,
) -> list[dict[str, Any]]:
    """Get pull requests from the authenticated user's dashboard across all projects.

    role: AUTHOR | REVIEWER | PARTICIPANT
    state: OPEN | MERGED | DECLINED | ALL
    participant_status: APPROVED | UNAPPROVED | NEEDS_WORK
    order: NEWEST | OLDEST | PARTICIPANT_STATUS | CLOSED_DATE | NEWEST_ACTIVITY
    closed_since: Unix timestamp (ms) — only return PRs closed after this time.
    """
```
to:
```python
async def get_dashboard_pull_requests(
    ctx: Context,
    role: Literal["AUTHOR", "REVIEWER", "PARTICIPANT"] | None = None,
    state: Literal["OPEN", "MERGED", "DECLINED"] | None = None,
    participant_status: Literal["APPROVED", "UNAPPROVED", "NEEDS_WORK"] | None = None,
    order: Literal["NEWEST", "OLDEST", "PARTICIPANT_STATUS", "CLOSED_DATE", "NEWEST_ACTIVITY"] | None = None,
    closed_since: int | None = None,
) -> list[dict[str, Any]]:
    """Get pull requests from the authenticated user's dashboard across all projects.

    role: AUTHOR | REVIEWER | PARTICIPANT
    state: OPEN | MERGED | DECLINED (omit for all states)
    participant_status: APPROVED | UNAPPROVED | NEEDS_WORK
    order: NEWEST | OLDEST | PARTICIPANT_STATUS | CLOSED_DATE | NEWEST_ACTIVITY
    closed_since: Unix timestamp (ms) — only return PRs closed after this time.
    """
```

- [ ] **Step 2: Run the dashboard schema test**

```bash
python -m pytest tests/test_server_registration.py::test_dashboard_pr_enum_schemas -v
```

Expected: PASS.

- [ ] **Step 3: Run full test suite**

```bash
make check
```

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add src/bitbucket_mcp/tools/dashboard.py
git commit -m "feat: use Literal types for all enum params in get_dashboard_pull_requests"
```

---

### Task 4: Update `tools/comments.py`

**Files:**
- Modify: `src/bitbucket_mcp/tools/comments.py`
- Modify: `tests/test_tools_comments.py`

- [ ] **Step 1: Remove the test for the guard we are about to delete**

In `tests/test_tools_comments.py`, remove this test entirely:

```python
@pytest.mark.asyncio
async def test_publish_review_invalid_status() -> None:
    ctx = _make_ctx(AsyncMock())
    with pytest.raises(ValueError, match="status must be"):
        await publish_review(ctx=ctx, repository="r", pr_id=1, status="UNKNOWN")
```

- [ ] **Step 2: Update `add_comment` state and `publish_review` status to `Literal`; remove manual guard**

Change the import at the top of `src/bitbucket_mcp/tools/comments.py` from:
```python
from typing import Any
```
to:
```python
from typing import Any, Literal
```

Change `add_comment` signature from:
```python
async def add_comment(
    ctx: Context,
    project: str | None = None,
    repository: str = "",
    pr_id: int = 0,
    text: str = "",
    state: str = "OPEN",
    parent_id: int | None = None,
) -> dict[str, Any]:
    """Add a comment to a pull request.

    state: OPEN (visible immediately) | PENDING (draft, publish later).
    parent_id: Comment ID to reply to (creates a threaded reply).
    """
```
to:
```python
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
```

Change `publish_review` signature from:
```python
async def publish_review(
    ctx: Context,
    project: str | None = None,
    repository: str = "",
    pr_id: int = 0,
    overall_comment: str | None = None,
    status: str = "APPROVED",
    reviewer_slug: str | None = None,
) -> dict[str, Any]:
    """Publish a PR review: post an overall comment and set participant status.

    status: APPROVED | UNAPPROVED | NEEDS_WORK
    reviewer_slug: Your Bitbucket username slug (auto-detected from PR participants if omitted).
    overall_comment: Optional overall review comment to post on the PR.
    """
    _require_write(ctx, "publish_review")
    valid_statuses = {"APPROVED", "UNAPPROVED", "NEEDS_WORK"}
    if status not in valid_statuses:
        raise ValueError(f"status must be one of {sorted(valid_statuses)}")
```
to:
```python
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
```

- [ ] **Step 3: Run schema tests for comments**

```bash
python -m pytest tests/test_server_registration.py::test_add_comment_state_enum_schema tests/test_server_registration.py::test_publish_review_status_enum_schema -v
```

Expected: Both PASS.

- [ ] **Step 4: Run full test suite**

```bash
make check
```

Expected: All tests pass (the removed test no longer causes a failure).

- [ ] **Step 5: Commit**

```bash
git add src/bitbucket_mcp/tools/comments.py tests/test_tools_comments.py
git commit -m "feat: use Literal types in comments tools, remove manual status guard"
```

---

### Task 5: Final verification

- [ ] **Step 1: Run the complete gate**

```bash
make check
```

Expected output includes:
- `ruff check` — no errors
- `mypy` — no errors (strict mode)
- `pytest` — all tests pass, including all 5 new `*_enum_schema` tests

- [ ] **Step 2: Spot-check the MCP schema output**

```bash
python -c "
import asyncio
from bitbucket_mcp.server import create_server
mcp = create_server()
tools = asyncio.run(mcp.list_tools())
for t in tools:
    if t.name in ('list_pull_requests', 'get_dashboard_pull_requests', 'add_comment', 'publish_review'):
        props = t.inputSchema.get('properties', {})
        for k, v in props.items():
            if 'enum' in v:
                print(f'{t.name}.{k}: {v[\"enum\"]}')
"
```

Expected: Each enum parameter prints its valid values. No `ALL` appears.

- [ ] **Step 3: Commit if any fixup was needed, otherwise done**
