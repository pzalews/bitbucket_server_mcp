from __future__ import annotations

import re
from typing import Any

import httpx
import structlog
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from .config import Settings
from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    BitbucketAPIError,
    ConflictError,
    NotFoundError,
    RateLimitError,
    StaleVersionError,
)

_SHA40_RE = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)

log = structlog.get_logger(__name__)


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, BitbucketAPIError):
        return exc.status_code >= 500
    return False


class BitbucketClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **settings.get_auth_headers(),
            **settings.get_custom_headers(),
        }
        self._http = httpx.AsyncClient(
            base_url=settings.bitbucket_url,
            headers=headers,
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> BitbucketClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()

    @retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        raw: bool = False,
    ) -> Any:
        response = await self._http.request(method, path, params=params, json=json)
        if response.status_code == 204:
            return None
        if response.status_code == 401:
            raise AuthenticationError(401, "Authentication failed — check credentials")
        if response.status_code == 403:
            raise AuthorizationError(403, "Insufficient permissions")
        if response.status_code == 404:
            raise NotFoundError(404, response.text)
        if response.status_code == 409:
            try:
                body = response.json() if response.content else {}
            except ValueError:
                body = {}
            errors: list[dict[str, Any]] = body.get("errors", [])
            msg = errors[0].get("message", "") if errors else ""
            if "out-of-date" in msg.lower() or "version" in msg.lower():
                raise StaleVersionError(409, msg, errors)
            raise ConflictError(409, msg, errors)
        if response.status_code == 429:
            raise RateLimitError(429, "Rate limited — retry after a moment")
        if response.status_code >= 400:
            try:
                body = response.json() if response.content else {}
            except ValueError:
                body = {}
            errors = body.get("errors", [])
            msg = errors[0].get("message", response.text) if errors else response.text
            raise BitbucketAPIError(response.status_code, msg, errors)
        if raw:
            return response.text
        if not response.content:
            return None
        return response.json()

    async def _get_paged(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        max_pages: int = 20,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        start = 0
        limit = 100
        base_params = dict(params or {})
        for _ in range(max_pages):
            page_params: dict[str, Any] = {**base_params, "start": start, "limit": limit}
            data = await self._request("GET", path, params=page_params)
            if not isinstance(data, dict):
                break
            values: list[dict[str, Any]] = data.get("values", [])
            results.extend(values)
            if data.get("isLastPage", True):
                break
            start = data.get("nextPageStart", start + limit)
        return results

    # ── Projects ──────────────────────────────────────────────────────────────
    async def list_projects(self) -> list[dict[str, Any]]:
        return await self._get_paged("/rest/api/1.0/projects")

    # ── Repositories ──────────────────────────────────────────────────────────
    async def list_repositories(self, project_key: str) -> list[dict[str, Any]]:
        return await self._get_paged(f"/rest/api/1.0/projects/{project_key}/repos")

    async def get_default_branch(self, project_key: str, repo_slug: str) -> dict[str, Any]:
        result = await self._request(
            "GET",
            f"/rest/api/1.0/projects/{project_key}/repos/{repo_slug}/branches/default",
        )
        return result  # type: ignore[return-value]

    async def browse_repository(
        self,
        project_key: str,
        repo_slug: str,
        path: str = "",
        at: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if at:
            params["at"] = at
        result = await self._request(
            "GET",
            f"/rest/api/1.0/projects/{project_key}/repos/{repo_slug}/browse/{path}",
            params=params or None,
        )
        return result  # type: ignore[return-value]

    async def get_file_content(
        self,
        project_key: str,
        repo_slug: str,
        path: str,
        at: str | None = None,
    ) -> str:
        params: dict[str, Any] = {}
        if at:
            params["at"] = at
        result = await self._request(
            "GET",
            f"/rest/api/1.0/projects/{project_key}/repos/{repo_slug}/raw/{path}",
            params=params or None,
            raw=True,
        )
        return result  # type: ignore[return-value]

    # ── Branches ──────────────────────────────────────────────────────────────
    async def list_branches(
        self,
        project_key: str,
        repo_slug: str,
        filter_text: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if filter_text:
            params["filterText"] = filter_text
        return await self._get_paged(
            f"/rest/api/1.0/projects/{project_key}/repos/{repo_slug}/branches",
            params=params or None,
        )

    async def create_branch(
        self,
        project_key: str,
        repo_slug: str,
        name: str,
        start_point: str,
    ) -> dict[str, Any]:
        branch_ref = name if name.startswith("refs/heads/") else f"refs/heads/{name}"
        start_ref = (
            start_point
            if start_point.startswith("refs/") or _SHA40_RE.match(start_point)
            else f"refs/heads/{start_point}"
        )
        result = await self._request(
            "POST",
            f"/rest/branch-utils/1.0/projects/{project_key}/repos/{repo_slug}/branches",
            json={"name": branch_ref, "startPoint": start_ref},
        )
        return result  # type: ignore[return-value]

    async def delete_branch(
        self, project_key: str, repo_slug: str, name: str
    ) -> None:
        branch_ref = name if name.startswith("refs/heads/") else f"refs/heads/{name}"
        await self._request(
            "DELETE",
            f"/rest/branch-utils/1.0/projects/{project_key}/repos/{repo_slug}/branches",
            json={"name": branch_ref, "dryRun": False},
        )

    # ── Commits ───────────────────────────────────────────────────────────────
    async def list_commits(
        self,
        project_key: str,
        repo_slug: str,
        branch: str | None = None,
        author: str | None = None,
        path: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if branch:
            params["until"] = branch
        if author:
            params["author"] = author
        if path:
            params["path"] = path
        return await self._get_paged(
            f"/rest/api/1.0/projects/{project_key}/repos/{repo_slug}/commits",
            params=params or None,
        )

    async def get_code_insights(
        self, project_key: str, repo_slug: str, commit_id: str
    ) -> list[dict[str, Any]]:
        return await self._get_paged(
            f"/rest/insights/1.0/projects/{project_key}/repos/{repo_slug}"
            f"/commits/{commit_id}/reports",
        )

    # ── Pull Requests ─────────────────────────────────────────────────────────
    async def list_pull_requests(
        self,
        project_key: str,
        repo_slug: str,
        state: str = "OPEN",
        author: str | None = None,
        direction: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"state": state}
        if author:
            params["author.name"] = author
        if direction:
            params["direction"] = direction
        return await self._get_paged(
            f"/rest/api/1.0/projects/{project_key}/repos/{repo_slug}/pull-requests",
            params=params,
        )

    async def get_pull_request(
        self, project_key: str, repo_slug: str, pr_id: int
    ) -> dict[str, Any]:
        result = await self._request(
            "GET",
            f"/rest/api/1.0/projects/{project_key}/repos/{repo_slug}/pull-requests/{pr_id}",
        )
        return result  # type: ignore[return-value]

    async def create_pull_request(
        self,
        project_key: str,
        repo_slug: str,
        title: str,
        description: str,
        source_branch: str,
        target_branch: str,
        source_project: str | None = None,
        source_repository: str | None = None,
        reviewers: list[str] | None = None,
    ) -> dict[str, Any]:
        src_proj = source_project or project_key
        src_repo = source_repository or repo_slug
        body: dict[str, Any] = {
            "title": title,
            "description": description,
            "state": "OPEN",
            "fromRef": {
                "id": source_branch,
                "repository": {"slug": src_repo, "project": {"key": src_proj}},
            },
            "toRef": {
                "id": target_branch,
                "repository": {"slug": repo_slug, "project": {"key": project_key}},
            },
            "reviewers": [{"user": {"name": r}} for r in (reviewers or [])],
        }
        result = await self._request(
            "POST",
            f"/rest/api/1.0/projects/{project_key}/repos/{repo_slug}/pull-requests",
            json=body,
        )
        return result  # type: ignore[return-value]

    async def get_default_reviewers(
        self,
        project_key: str,
        repo_slug: str,
        source_branch: str,
        target_branch: str,
    ) -> list[dict[str, Any]]:
        result = await self._request(
            "GET",
            f"/rest/default-reviewers/1.0/projects/{project_key}/repos/{repo_slug}/reviewers",
            params={"sourceRefId": source_branch, "targetRefId": target_branch},
        )
        if isinstance(result, list):
            return result
        return []

    async def update_pull_request(
        self,
        project_key: str,
        repo_slug: str,
        pr_id: int,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        result = await self._request(
            "PUT",
            f"/rest/api/1.0/projects/{project_key}/repos/{repo_slug}/pull-requests/{pr_id}",
            json=updates,
        )
        return result  # type: ignore[return-value]

    async def merge_pull_request(
        self,
        project_key: str,
        repo_slug: str,
        pr_id: int,
        version: int,
        strategy: str = "merge-commit",
    ) -> dict[str, Any]:
        strategy_map = {
            "merge-commit": "no-ff",
            "squash": "squash",
            "fast-forward": "ff",
        }
        result = await self._request(
            "POST",
            f"/rest/api/1.0/projects/{project_key}/repos/{repo_slug}/pull-requests/{pr_id}/merge",
            params={"version": version},
            json={"strategyId": strategy_map.get(strategy, "no-ff")},
        )
        return result  # type: ignore[return-value]

    async def decline_pull_request(
        self, project_key: str, repo_slug: str, pr_id: int, version: int
    ) -> dict[str, Any]:
        result = await self._request(
            "POST",
            f"/rest/api/1.0/projects/{project_key}/repos/{repo_slug}/pull-requests/{pr_id}/decline",
            params={"version": version},
        )
        return result  # type: ignore[return-value]

    async def approve_pull_request(
        self, project_key: str, repo_slug: str, pr_id: int
    ) -> dict[str, Any]:
        result = await self._request(
            "POST",
            f"/rest/api/1.0/projects/{project_key}/repos/{repo_slug}/pull-requests/{pr_id}/approve",
        )
        return result  # type: ignore[return-value]

    async def unapprove_pull_request(
        self, project_key: str, repo_slug: str, pr_id: int
    ) -> None:
        await self._request(
            "DELETE",
            f"/rest/api/1.0/projects/{project_key}/repos/{repo_slug}/pull-requests/{pr_id}/approve",
        )

    async def get_pull_request_diff(
        self,
        project_key: str,
        repo_slug: str,
        pr_id: int,
        context_lines: int = 10,
    ) -> dict[str, Any]:
        result = await self._request(
            "GET",
            f"/rest/api/1.0/projects/{project_key}/repos/{repo_slug}/pull-requests/{pr_id}/diff",
            params={"contextLines": context_lines, "whitespace": "IGNORE_ALL"},
        )
        return result  # type: ignore[return-value]

    async def get_pull_request_activities(
        self, project_key: str, repo_slug: str, pr_id: int
    ) -> list[dict[str, Any]]:
        return await self._get_paged(
            f"/rest/api/1.0/projects/{project_key}/repos/{repo_slug}"
            f"/pull-requests/{pr_id}/activities",
        )

    async def get_pull_request_comments(
        self, project_key: str, repo_slug: str, pr_id: int
    ) -> list[dict[str, Any]]:
        return await self._get_paged(
            f"/rest/api/1.0/projects/{project_key}/repos/{repo_slug}"
            f"/pull-requests/{pr_id}/comments",
        )

    async def get_comment(
        self, project_key: str, repo_slug: str, pr_id: int, comment_id: int
    ) -> dict[str, Any]:
        result = await self._request(
            "GET",
            f"/rest/api/1.0/projects/{project_key}/repos/{repo_slug}"
            f"/pull-requests/{pr_id}/comments/{comment_id}",
        )
        return result  # type: ignore[return-value]

    async def get_pull_request_participants(
        self, project_key: str, repo_slug: str, pr_id: int
    ) -> list[dict[str, Any]]:
        pr = await self.get_pull_request(project_key, repo_slug, pr_id)
        return pr.get("participants", [])  # type: ignore[return-value]

    async def add_comment(
        self,
        project_key: str,
        repo_slug: str,
        pr_id: int,
        text: str,
        state: str = "OPEN",
        parent_id: int | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"text": text, "state": state}
        if parent_id is not None:
            body["parent"] = {"id": parent_id}
        result = await self._request(
            "POST",
            f"/rest/api/1.0/projects/{project_key}/repos/{repo_slug}"
            f"/pull-requests/{pr_id}/comments",
            json=body,
        )
        return result  # type: ignore[return-value]

    async def add_comment_inline(
        self,
        project_key: str,
        repo_slug: str,
        pr_id: int,
        text: str,
        file_path: str,
        line_number: int,
        line_type: str = "ADDED",
        file_type: str = "TO",
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "text": text,
            "anchor": {
                "line": line_number,
                "lineType": line_type,
                "fileType": file_type,
                "path": file_path,
            },
        }
        result = await self._request(
            "POST",
            f"/rest/api/1.0/projects/{project_key}/repos/{repo_slug}"
            f"/pull-requests/{pr_id}/comments",
            json=body,
        )
        return result  # type: ignore[return-value]

    async def edit_comment(
        self,
        project_key: str,
        repo_slug: str,
        pr_id: int,
        comment_id: int,
        text: str,
        version: int,
    ) -> dict[str, Any]:
        result = await self._request(
            "PUT",
            f"/rest/api/1.0/projects/{project_key}/repos/{repo_slug}"
            f"/pull-requests/{pr_id}/comments/{comment_id}",
            json={"text": text, "version": version},
        )
        return result  # type: ignore[return-value]

    async def delete_comment(
        self,
        project_key: str,
        repo_slug: str,
        pr_id: int,
        comment_id: int,
        version: int,
    ) -> None:
        await self._request(
            "DELETE",
            f"/rest/api/1.0/projects/{project_key}/repos/{repo_slug}"
            f"/pull-requests/{pr_id}/comments/{comment_id}",
            params={"version": version},
        )

    async def update_participant_status(
        self,
        project_key: str,
        repo_slug: str,
        pr_id: int,
        user_slug: str,
        status: str,
    ) -> dict[str, Any]:
        result = await self._request(
            "PUT",
            f"/rest/api/1.0/projects/{project_key}/repos/{repo_slug}"
            f"/pull-requests/{pr_id}/participants/{user_slug}",
            json={"user": {"name": user_slug}, "status": status},
        )
        return result  # type: ignore[return-value]

    # ── Search ────────────────────────────────────────────────────────────────
    async def search(
        self,
        query: str,
        project_key: str | None = None,
        repo_slug: str | None = None,
        limit: int = 25,
    ) -> dict[str, Any]:
        scope: dict[str, Any] = {}
        if project_key:
            scope["project"] = {"key": project_key}
            if repo_slug:
                scope["repository"] = {"slug": repo_slug}
        body: dict[str, Any] = {
            "query": query,
            "entities": {"code": {"limit": limit}},
        }
        if scope:
            body["scope"] = scope
        result = await self._request("POST", "/rest/search/latest/search", json=body)
        return result  # type: ignore[return-value]

    # ── Dashboard ─────────────────────────────────────────────────────────────
    async def get_dashboard_pull_requests(
        self,
        role: str | None = None,
        state: str | None = None,
        participant_status: str | None = None,
        order: str | None = None,
        closed_since: int | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if role:
            params["role"] = role
        if state:
            params["state"] = state
        if participant_status:
            params["participantStatus"] = participant_status
        if order:
            params["order"] = order
        if closed_since:
            params["closedSince"] = closed_since
        return await self._get_paged(
            "/rest/api/1.0/dashboard/pull-requests",
            params=params or None,
        )
