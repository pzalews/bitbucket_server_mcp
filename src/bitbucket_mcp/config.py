"""Configuration for Bitbucket Server MCP.

Reads from environment variables (BITBUCKET_* and MCP_*) or a .env file.
"""

from __future__ import annotations

import base64
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Bitbucket connection
    bitbucket_url: str
    bitbucket_token: str | None = None
    bitbucket_username: str | None = None
    bitbucket_password: str | None = None

    # Behaviour options
    bitbucket_default_project: str | None = None
    bitbucket_diff_max_lines_per_file: int = Field(default=500, ge=1)
    bitbucket_log_path: str | None = None
    bitbucket_read_only: bool = False
    bitbucket_custom_headers: str | None = None  # "Header=Val,Other=Val=WithEquals"

    # Transport
    mcp_transport: Literal["stdio", "http"] = "stdio"
    mcp_http_host: str = "127.0.0.1"
    mcp_http_port: int = Field(default=8000, gt=0, le=65535)

    @field_validator("bitbucket_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.rstrip("/")
        if not v.startswith(("http://", "https://")):
            raise ValueError(
                f"BITBUCKET_URL must start with http:// or https://, got: {v!r}"
            )
        return v

    @model_validator(mode="after")
    def require_auth(self) -> Settings:
        has_pat = bool(self.bitbucket_token and self.bitbucket_token.strip())
        has_basic = (
            bool(self.bitbucket_username and self.bitbucket_username.strip())
            and bool(self.bitbucket_password and self.bitbucket_password.strip())
        )
        if not has_pat and not has_basic:
            raise ValueError(
                "Set BITBUCKET_TOKEN or both BITBUCKET_USERNAME and BITBUCKET_PASSWORD"
            )
        return self

    def get_auth_headers(self) -> dict[str, str]:
        token = self.bitbucket_token and self.bitbucket_token.strip()
        if token:
            return {"Authorization": f"Bearer {token}"}
        creds = base64.b64encode(
            f"{self.bitbucket_username}:{self.bitbucket_password}".encode()
        ).decode()
        return {"Authorization": f"Basic {creds}"}

    def get_custom_headers(self) -> dict[str, str]:
        """Parse comma-separated Header=Value pairs; values may contain '='."""
        if not self.bitbucket_custom_headers:
            return {}
        result: dict[str, str] = {}
        for pair in self.bitbucket_custom_headers.split(","):
            key, sep, value = pair.strip().partition("=")
            key = key.strip()
            if key and sep:  # skip pairs without a '=' separator
                result[key] = value.strip()
        return result

    def redacted(self) -> dict[str, object]:
        return {
            "bitbucket_url": self.bitbucket_url,
            "auth_method": "token" if self.bitbucket_token else "basic",
            "default_project": self.bitbucket_default_project,
            "read_only": self.bitbucket_read_only,
            "transport": self.mcp_transport,
            "http_host": self.mcp_http_host,
            "http_port": self.mcp_http_port,
            "diff_max_lines": self.bitbucket_diff_max_lines_per_file,
            "custom_headers_count": len(self.get_custom_headers()),
        }
