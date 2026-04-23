# Bitbucket Server MCP

FastMCP server for Bitbucket Server (self-hosted / Data Center). Provides 28 MCP tools for managing projects, repositories, pull requests, comments, branches, and code insights.

## Prerequisites

- Python 3.12+
- `uv` (recommended) or `pip`
- Bitbucket Server 6.x+ (or Bitbucket Data Center)
- Personal Access Token **or** username/password credentials

## Installation

```bash
git clone <repo>
cd bitbucket_server_mcp
uv pip install -e .
```

## Configuration

Copy `.env.example` to `.env` and fill in your values, or set environment variables directly.

| Variable | Required | Description |
|---|---|---|
| `BITBUCKET_URL` | Yes | Base URL of your Bitbucket Server (e.g. `https://bitbucket.company.com`) |
| `BITBUCKET_TOKEN` | Auth* | Personal Access Token |
| `BITBUCKET_USERNAME` | Auth* | Username for basic auth |
| `BITBUCKET_PASSWORD` | Auth* | Password for basic auth |
| `BITBUCKET_DEFAULT_PROJECT` | No | Default project key (avoids passing `project` to every tool) |
| `BITBUCKET_DIFF_MAX_LINES_PER_FILE` | No | Max diff lines per file (default: 500) |
| `BITBUCKET_LOG_PATH` | No | Write structured JSON logs to this file path |
| `BITBUCKET_READ_ONLY` | No | Set `true` to block all write operations |
| `BITBUCKET_CUSTOM_HEADERS` | No | Extra headers: `Header=Val,Other=Val=WithEquals` |
| `MCP_TRANSPORT` | No | `stdio` (default) or `http` |
| `MCP_HTTP_HOST` | No | HTTP host (default: `127.0.0.1`) |
| `MCP_HTTP_PORT` | No | HTTP port (default: `8000`) |

*Provide either `BITBUCKET_TOKEN` **or** both `BITBUCKET_USERNAME` + `BITBUCKET_PASSWORD`.

## Authentication

**Token (recommended):**
```bash
BITBUCKET_TOKEN=your-pat-here
```

**Basic auth:**
```bash
BITBUCKET_USERNAME=alice
BITBUCKET_PASSWORD=secret
```

## Running

**stdio (for Claude Desktop / local use):**
```bash
python -m bitbucket_mcp
```

**HTTP (for remote / multi-client use):**
```bash
MCP_TRANSPORT=http python -m bitbucket_mcp
# Server starts at http://127.0.0.1:8000/mcp/
```

**Docker:**
```bash
cp .env.example .env  # fill in values
docker-compose up
```

## MCP Client Configuration

**Claude Desktop (stdio)** — add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "bitbucket": {
      "command": "python",
      "args": ["-m", "bitbucket_mcp"],
      "env": {
        "BITBUCKET_URL": "https://bitbucket.yourcompany.com",
        "BITBUCKET_TOKEN": "your-pat"
      }
    }
  }
}
```

**HTTP transport** — add to your MCP client config:
```json
{
  "mcpServers": {
    "bitbucket": {
      "transport": "streamable-http",
      "url": "http://localhost:8000/mcp/"
    }
  }
}
```

## Tool Catalog

| Tool | Type | Description |
|---|---|---|
| `list_projects` | Read | List all accessible projects |
| `list_repositories` | Read | List repositories in a project |
| `browse_repository` | Read | Browse file tree in a repo |
| `get_file_content` | Read | Get raw file content |
| `list_branches` | Read | List branches (with filter) |
| `create_branch` | Write | Create branch from ref or SHA |
| `delete_branch` | Write | Delete branch (default branch protected) |
| `list_commits` | Read | List commit history |
| `get_code_insights` | Read | Get CI/code analysis reports for a commit |
| `create_pull_request` | Write | Open a new PR |
| `update_pull_request` | Write | Update PR title/description/reviewers |
| `get_pull_request` | Read | Get PR details |
| `list_pull_requests` | Read | List PRs with filters |
| `merge_pull_request` | Write | Merge PR (auto-fetches version) |
| `decline_pull_request` | Write | Decline PR |
| `approve_pull_request` | Write | Approve PR |
| `unapprove_pull_request` | Write | Retract approval |
| `add_comment` | Write | Add PR comment (OPEN or PENDING) |
| `add_comment_inline` | Write | Add inline comment on a diff line |
| `get_comments` | Read | List all PR comments |
| `edit_comment` | Write | Edit comment (auto-fetches version) |
| `delete_comment` | Write | Delete comment (auto-fetches version) |
| `publish_review` | Write | Post overall review comment + set status |
| `get_diff` | Read | Get PR diff with truncation |
| `get_reviews` | Read | Get reviewer list with approval status |
| `get_activities` | Read | Get PR activity stream |
| `search` | Read | Search code (requires Search plugin) |
| `get_dashboard_pull_requests` | Read | Get PRs from your dashboard |

## Read-Only Mode

Set `BITBUCKET_READ_ONLY=true` to block all write operations at runtime. All read tools continue to work. Write tools return a clear error message immediately without making any API calls.

## Custom Headers (Zero Trust / Proxies)

Use `BITBUCKET_CUSTOM_HEADERS` to inject headers on every request:

```bash
BITBUCKET_CUSTOM_HEADERS="X-Zero-Trust-Token=your-zt-token,X-Forwarded-Host=internal.proxy"
```

Values may contain `=` characters; only the first `=` in each pair is used as the separator.

## Multiple Instances

Each process targets exactly one Bitbucket Server. To connect to multiple servers, run one process per server with different env vars, and register each under a different name in your MCP client config.

## Security Notes

- Credentials are never logged. Logs show `auth_method: token/basic` only.
- Custom header values are redacted from the effective config resource.
- The default branch of any repository cannot be deleted via `delete_branch`.
- Merge strategy is validated against an allowlist (`merge-commit`, `squash`, `fast-forward`).
- All tool inputs are validated by the FastMCP schema before execution.

## Development

```bash
make install    # install with dev deps
make test       # run all tests
make lint       # ruff lint
make typecheck  # mypy
make check      # lint + typecheck + test
```

## API Assumptions

- Branches are managed via the `branch-utils/1.0` REST API (not `api/1.0`).
- Code Insights require Bitbucket Server 7.x+ or the relevant plugin.
- `search` requires the Bitbucket Server Search plugin.
- `get_file_content` uses the `/raw/` endpoint; binary files return raw bytes as text.
- `merge_pull_request` uses `strategyId` (Bitbucket Data Center 7.x+); older instances may ignore the strategy.
