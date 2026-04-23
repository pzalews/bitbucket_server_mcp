from __future__ import annotations

import httpx
import pytest
import respx

from bitbucket_mcp.client import BitbucketClient
from bitbucket_mcp.config import Settings
from bitbucket_mcp.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    StaleVersionError,
)

BASE = "https://bb.example.com"


@pytest.fixture
def settings() -> Settings:
    return Settings(bitbucket_url=BASE, bitbucket_token="test-token")


@pytest.mark.asyncio
@respx.mock
async def test_list_projects(settings: Settings) -> None:
    respx.get(f"{BASE}/rest/api/1.0/projects").mock(
        return_value=httpx.Response(
            200,
            json={"values": [{"key": "PROJ", "name": "My Project"}], "isLastPage": True},
        )
    )
    async with BitbucketClient(settings) as client:
        result = await client.list_projects()
    assert result == [{"key": "PROJ", "name": "My Project"}]


@pytest.mark.asyncio
@respx.mock
async def test_get_pull_request_404(settings: Settings) -> None:
    respx.get(f"{BASE}/rest/api/1.0/projects/PROJ/repos/myrepo/pull-requests/999").mock(
        return_value=httpx.Response(404, text="Not found")
    )
    async with BitbucketClient(settings) as client:
        with pytest.raises(NotFoundError):
            await client.get_pull_request("PROJ", "myrepo", 999)


@pytest.mark.asyncio
@respx.mock
async def test_merge_pr_stale_version(settings: Settings) -> None:
    respx.post(
        f"{BASE}/rest/api/1.0/projects/PROJ/repos/myrepo/pull-requests/1/merge"
    ).mock(
        return_value=httpx.Response(
            409,
            json={
                "errors": [
                    {"message": "out-of-date: version mismatch"}
                ]
            },
        )
    )
    async with BitbucketClient(settings) as client:
        with pytest.raises(StaleVersionError):
            await client.merge_pull_request("PROJ", "myrepo", 1, version=0)


@pytest.mark.asyncio
@respx.mock
async def test_create_branch_conflict(settings: Settings) -> None:
    respx.post(
        f"{BASE}/rest/branch-utils/1.0/projects/PROJ/repos/myrepo/branches"
    ).mock(
        return_value=httpx.Response(
            409,
            json={"errors": [{"message": "Branch already exists"}]},
        )
    )
    async with BitbucketClient(settings) as client:
        with pytest.raises(ConflictError):
            await client.create_branch("PROJ", "myrepo", "feature/x", "main")


@pytest.mark.asyncio
@respx.mock
async def test_auth_error(settings: Settings) -> None:
    respx.get(f"{BASE}/rest/api/1.0/projects").mock(
        return_value=httpx.Response(401, text="Unauthorized")
    )
    async with BitbucketClient(settings) as client:
        with pytest.raises(AuthenticationError):
            await client.list_projects()


@pytest.mark.asyncio
@respx.mock
async def test_pagination_collects_all_pages(settings: Settings) -> None:
    respx.get(f"{BASE}/rest/api/1.0/projects").mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "values": [{"key": "A"}],
                    "isLastPage": False,
                    "nextPageStart": 100,
                },
            ),
            httpx.Response(
                200,
                json={"values": [{"key": "B"}], "isLastPage": True},
            ),
        ]
    )
    async with BitbucketClient(settings) as client:
        result = await client.list_projects()
    assert len(result) == 2
    assert result[0]["key"] == "A"
    assert result[1]["key"] == "B"
