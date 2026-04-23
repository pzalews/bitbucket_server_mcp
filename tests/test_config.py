import base64

import pytest
from pydantic import ValidationError

from bitbucket_mcp.config import Settings


def make_settings(**kwargs: object) -> Settings:
    base: dict[str, object] = {"bitbucket_url": "https://bb.example.com", "bitbucket_token": "tok"}
    base.update(kwargs)
    return Settings(**base)  # type: ignore[arg-type]


def test_requires_auth() -> None:
    with pytest.raises(ValidationError):
        Settings(bitbucket_url="https://bb.example.com")  # no auth


def test_strips_trailing_slash() -> None:
    s = make_settings(bitbucket_url="https://bb.example.com/")
    assert s.bitbucket_url == "https://bb.example.com"


def test_rejects_url_without_scheme() -> None:
    with pytest.raises(ValidationError, match="http"):
        make_settings(bitbucket_url="bb.example.com")


def test_token_auth_header() -> None:
    s = make_settings()
    assert s.get_auth_headers() == {"Authorization": "Bearer tok"}


def test_basic_auth_header() -> None:
    s = Settings(
        bitbucket_url="https://bb.example.com",
        bitbucket_username="user",
        bitbucket_password="pass",
    )
    expected = base64.b64encode(b"user:pass").decode()
    assert s.get_auth_headers() == {"Authorization": f"Basic {expected}"}


def test_whitespace_only_token_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(bitbucket_url="https://bb.example.com", bitbucket_token="   ")


def test_custom_headers_with_equals_in_value() -> None:
    s = make_settings(bitbucket_custom_headers="X-Token=abc=def,X-Other=val")
    headers = s.get_custom_headers()
    assert headers["X-Token"] == "abc=def"
    assert headers["X-Other"] == "val"


def test_custom_headers_without_equals_skipped() -> None:
    s = make_settings(bitbucket_custom_headers="X-NoPair,X-OK=val")
    headers = s.get_custom_headers()
    assert "X-NoPair" not in headers
    assert headers["X-OK"] == "val"


def test_custom_headers_empty() -> None:
    s = make_settings()
    assert s.get_custom_headers() == {}


def test_read_only_defaults_false() -> None:
    s = make_settings()
    assert s.bitbucket_read_only is False


def test_redacted_omits_secrets() -> None:
    secret = "super-secret-pat-value"
    s = Settings(bitbucket_url="https://bb.example.com", bitbucket_token=secret)
    d = s.redacted()
    assert not any(v == secret for v in d.values())
    assert d["auth_method"] == "token"
    assert "http_host" in d
    assert "http_port" in d


def test_diff_max_lines_default() -> None:
    s = make_settings()
    assert s.bitbucket_diff_max_lines_per_file == 500


def test_invalid_port_rejected() -> None:
    with pytest.raises(ValidationError):
        make_settings(mcp_http_port=99999)


def test_invalid_transport_rejected() -> None:
    with pytest.raises(ValidationError):
        make_settings(mcp_transport="grpc")  # type: ignore[arg-type]
