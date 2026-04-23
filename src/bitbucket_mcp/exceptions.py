"""Typed exceptions for Bitbucket Server MCP."""

from __future__ import annotations


class BitbucketMCPError(Exception):
    """Base for all domain exceptions."""


class BitbucketAPIError(BitbucketMCPError):
    def __init__(
        self,
        status_code: int,
        message: str,
        errors: list[dict[str, object]] | None = None,
    ) -> None:
        self.status_code = status_code
        self.errors = errors or []
        super().__init__(f"HTTP {status_code}: {message}")


class NotFoundError(BitbucketAPIError):
    """404 — resource not found."""


class AuthenticationError(BitbucketAPIError):
    """401 — authentication failed."""


class AuthorizationError(BitbucketAPIError):
    """403 — insufficient permissions."""


class ConflictError(BitbucketAPIError):
    """409 — generic conflict (e.g., branch already exists)."""


class StaleVersionError(ConflictError):
    """409 — optimistic locking version mismatch."""


class RateLimitError(BitbucketAPIError):
    """429 — rate limited."""


class ReadOnlyModeError(BitbucketMCPError):
    """Raised when a write tool is called with BITBUCKET_READ_ONLY=true."""

    def __init__(self, tool_name: str) -> None:
        super().__init__(
            f"Tool '{tool_name}' is a write operation blocked by read-only mode "
            f"(BITBUCKET_READ_ONLY=true)."
        )


class DefaultBranchProtectionError(BitbucketMCPError):
    """Raised when attempting to delete the repository's default branch."""


class ConfigurationError(BitbucketMCPError):
    """Raised for invalid or missing configuration."""
