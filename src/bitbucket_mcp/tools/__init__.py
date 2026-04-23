from __future__ import annotations

from fastmcp import FastMCP

from .branches import create_branch, delete_branch, list_branches
from .comments import (
    add_comment,
    add_comment_inline,
    delete_comment,
    edit_comment,
    get_comments,
    publish_review,
)
from .commits import get_code_insights, list_commits
from .dashboard import get_dashboard_pull_requests
from .projects import list_projects
from .pull_requests import (
    approve_pull_request,
    create_pull_request,
    decline_pull_request,
    get_pull_request,
    list_pull_requests,
    merge_pull_request,
    unapprove_pull_request,
    update_pull_request,
)
from .repositories import browse_repository, get_file_content, list_repositories
from .reviews import get_activities, get_diff, get_reviews
from .search import search


def register_all_tools(mcp: FastMCP) -> None:
    for fn in [
        list_projects,
        list_repositories,
        browse_repository,
        get_file_content,
        list_branches,
        create_branch,
        delete_branch,
        list_commits,
        get_code_insights,
        create_pull_request,
        update_pull_request,
        get_pull_request,
        list_pull_requests,
        merge_pull_request,
        decline_pull_request,
        approve_pull_request,
        unapprove_pull_request,
        add_comment,
        add_comment_inline,
        get_comments,
        edit_comment,
        delete_comment,
        publish_review,
        get_diff,
        get_reviews,
        get_activities,
        search,
        get_dashboard_pull_requests,
    ]:
        mcp.add_tool(fn)
