.PHONY: install test lint typecheck format run-stdio run-http docker-build docker-run clean

install:
	uv pip install -e ".[dev]"

test:
	python -m pytest tests/ -v

test-coverage:
	python -m pytest tests/ --cov=bitbucket_mcp --cov-report=term-missing

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

typecheck:
	mypy src/

check: lint typecheck test

run-stdio:
	python -m bitbucket_mcp

run-http:
	MCP_TRANSPORT=http MCP_HTTP_HOST=127.0.0.1 MCP_HTTP_PORT=8000 python -m bitbucket_mcp

docker-build:
	docker build -t bitbucket-server-mcp .

docker-run:
	docker-compose up

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	rm -rf .pytest_cache .mypy_cache .ruff_cache dist
