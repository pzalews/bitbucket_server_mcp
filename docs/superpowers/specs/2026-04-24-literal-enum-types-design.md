# Design: Replace `str` enum parameters with `Literal` types

**Date:** 2026-04-24
**Status:** Approved

## Problem

Several tool functions accept enum-like string parameters (e.g. `state`, `role`, `direction`) typed as plain `str`. The Bitbucket Server API rejects invalid values with HTTP 400, producing a full traceback in logs. Worse, docstrings advertise `ALL` as a valid `state` value when the API does not accept it — causing guaranteed failures when an LLM passes it.

The only existing validation is a manual `valid_statuses` set check in `set_review_status` (`comments.py`), which is inconsistent and does not help with the MCP schema seen by LLMs.

## Goal

- Replace all enum-like `str` parameters in tool functions with precise `Literal` types.
- Remove the `ALL` pseudo-value from `state` documentation and accepted values. `state=None` means "no filter" (all states).
- Remove the manual `valid_statuses` guard in `set_review_status` — made redundant by `Literal` typing and FastMCP schema enforcement.
- Add negative tests confirming invalid values are rejected before any HTTP call.

## Scope

No changes to `client.py`. All fixes are at the tool layer only.

## Changes

### `tools/pull_requests.py`

| Parameter | Old type | New type |
|---|---|---|
| `state` | `str = "OPEN"` | `Literal["OPEN", "MERGED", "DECLINED"] = "OPEN"` |
| `direction` | `str \| None = None` | `Literal["INCOMING", "OUTGOING"] \| None = None` |

Docstring: remove `ALL` from `state` description.

### `tools/dashboard.py`

| Parameter | Old type | New type |
|---|---|---|
| `state` | `str \| None = None` | `Literal["OPEN", "MERGED", "DECLINED"] \| None = None` |
| `role` | `str \| None = None` | `Literal["AUTHOR", "REVIEWER", "PARTICIPANT"] \| None = None` |
| `participant_status` | `str \| None = None` | `Literal["APPROVED", "UNAPPROVED", "NEEDS_WORK"] \| None = None` |
| `order` | `str \| None = None` | `Literal["NEWEST", "OLDEST", "PARTICIPANT_STATUS", "CLOSED_DATE", "NEWEST_ACTIVITY"] \| None = None` |

Docstring: remove `ALL` from `state` description.

### `tools/comments.py`

| Parameter | Old type | New type |
|---|---|---|
| `state` (add_comment) | `str = "OPEN"` | `Literal["OPEN", "PENDING"] = "OPEN"` |
| `status` (set_review_status) | `str = "APPROVED"` | `Literal["APPROVED", "UNAPPROVED", "NEEDS_WORK"] = "APPROVED"` |

Remove manual `valid_statuses` set check and the `ValueError` guard in `set_review_status` — FastMCP schema enforcement handles this.

## Error handling

FastMCP validates `Literal` types before the tool function body runs. Invalid values are rejected at the MCP boundary with a type validation error — no HTTP call is made, no traceback from the Bitbucket API.

## Testing

Add negative tests for each affected tool confirming that passing an invalid value (e.g. `"ALL"`, `"INVALID"`) raises a validation error and does not reach the HTTP client. Existing positive tests (passing `"OPEN"`, etc.) remain unchanged.

## Out of scope

- `client.py` validation — internal layer covered by mypy once tool signatures are correct.
- New enum classes or a shared `enums.py` module.
