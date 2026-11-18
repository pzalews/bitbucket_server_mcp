# Base image pinned by digest; Dependabot (docker ecosystem) proposes updates.
ARG PYTHON_IMAGE=python:3.12-slim-trixie@sha256:05a994d2344eb364cc186910f4fc8786a38215f39f00d0acc25bff33a08f4177

FROM ${PYTHON_IMAGE} AS builder

WORKDIR /app

# uv binary only in the builder stage (kept out of site-packages, so not shipped at runtime).
COPY --from=ghcr.io/astral-sh/uv:0.13.9@sha256:49fe3c925d4b7a84ba2ef19883307bba2bbcf929a22040afb46f2dd092d13aeb /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock README.md ./
COPY src/ src/

# Install exactly the versions pinned in uv.lock (fails if the lockfile is stale).
RUN uv export --frozen --no-dev --no-emit-project -o /tmp/requirements.txt \
    && uv pip install --system --no-cache -r /tmp/requirements.txt \
    && uv pip install --system --no-cache --no-deps .

FROM ${PYTHON_IMAGE}

# Pick up Debian security fixes released after the base image was built.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/bitbucket-mcp /usr/local/bin/bitbucket-mcp
COPY src/ src/

RUN useradd -r -s /bin/false mcp && mkdir -p /var/log/bitbucket-mcp && chown mcp /var/log/bitbucket-mcp
USER mcp

ENV MCP_TRANSPORT=http
ENV MCP_HTTP_HOST=0.0.0.0
ENV MCP_HTTP_PORT=8000

EXPOSE 8000

ENTRYPOINT ["bitbucket-mcp"]
