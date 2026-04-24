from __future__ import annotations

import asyncio

from bitbucket_mcp.server import create_server


def test_all_tools_registered() -> None:
    mcp = create_server()
    tools = asyncio.run(mcp.list_tools())
    tool_names = {t.name for t in tools}
    expected = {
        "list_projects",
        "list_repositories",
        "browse_repository",
        "get_file_content",
        "list_branches",
        "create_branch",
        "delete_branch",
        "list_commits",
        "get_code_insights",
        "create_pull_request",
        "update_pull_request",
        "get_pull_request",
        "list_pull_requests",
        "merge_pull_request",
        "decline_pull_request",
        "approve_pull_request",
        "unapprove_pull_request",
        "add_comment",
        "add_comment_inline",
        "get_comments",
        "edit_comment",
        "delete_comment",
        "publish_review",
        "get_diff",
        "get_reviews",
        "get_activities",
        "search",
        "get_dashboard_pull_requests",
    }
    missing = expected - tool_names
    assert not missing, f"Tools not registered: {missing}"


def test_resource_count() -> None:
    mcp = create_server()

    async def _count() -> int:
        resources = await mcp.list_resources()
        templates = await mcp.list_resource_templates()
        return len(resources) + len(templates)

    total = asyncio.run(_count())
    assert total >= 4


def test_prompt_registered() -> None:
    mcp = create_server()
    prompts = asyncio.run(mcp.list_prompts())
    names = {p.name for p in prompts}
    assert "review_pull_request_prompt" in names


def _enum_values(schema: dict) -> set[str]:
    """Extract enum values from a JSON schema property (handles anyOf for optional Literals)."""
    if "enum" in schema:
        return set(schema["enum"])
    for item in schema.get("anyOf", []):
        if "enum" in item:
            return set(item["enum"])
    raise AssertionError(f"No enum found in schema: {schema}")


def test_pull_request_state_enum_schema() -> None:
    mcp = create_server()
    tools = asyncio.run(mcp.list_tools())
    tool = next(t for t in tools if t.name == "list_pull_requests")
    props = tool.to_mcp_tool().inputSchema["properties"]
    assert _enum_values(props["state"]) == {"OPEN", "MERGED", "DECLINED"}


def test_pull_request_direction_enum_schema() -> None:
    mcp = create_server()
    tools = asyncio.run(mcp.list_tools())
    tool = next(t for t in tools if t.name == "list_pull_requests")
    props = tool.to_mcp_tool().inputSchema["properties"]
    assert _enum_values(props["direction"]) == {"INCOMING", "OUTGOING"}


def test_dashboard_pr_enum_schemas() -> None:
    mcp = create_server()
    tools = asyncio.run(mcp.list_tools())
    tool = next(t for t in tools if t.name == "get_dashboard_pull_requests")
    props = tool.to_mcp_tool().inputSchema["properties"]
    assert _enum_values(props["state"]) == {"OPEN", "MERGED", "DECLINED"}
    assert _enum_values(props["role"]) == {"AUTHOR", "REVIEWER", "PARTICIPANT"}
    assert _enum_values(props["participant_status"]) == {"APPROVED", "UNAPPROVED", "NEEDS_WORK"}
    assert _enum_values(props["order"]) == {
        "NEWEST", "OLDEST", "PARTICIPANT_STATUS", "CLOSED_DATE", "NEWEST_ACTIVITY"
    }


def test_add_comment_state_enum_schema() -> None:
    mcp = create_server()
    tools = asyncio.run(mcp.list_tools())
    tool = next(t for t in tools if t.name == "add_comment")
    props = tool.to_mcp_tool().inputSchema["properties"]
    assert _enum_values(props["state"]) == {"OPEN", "PENDING"}


def test_publish_review_status_enum_schema() -> None:
    mcp = create_server()
    tools = asyncio.run(mcp.list_tools())
    tool = next(t for t in tools if t.name == "publish_review")
    props = tool.to_mcp_tool().inputSchema["properties"]
    assert _enum_values(props["status"]) == {"APPROVED", "UNAPPROVED", "NEEDS_WORK"}
