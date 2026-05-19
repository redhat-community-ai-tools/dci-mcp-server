# Single-stage build
FROM python:3.14-slim

# Install uv for dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set uv environment variables
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --frozen

# Run the MCP server app
CMD ["uv", "run", "main.py"]
