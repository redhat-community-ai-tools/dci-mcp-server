# Single-stage build
FROM python:3.14-slim@sha256:44dd04494ee8f3b538294360e7c4b3acb87c8268e4d0a4828a6500b1eff50061

# Install uv for dependency management
COPY --from=ghcr.io/astral-sh/uv:0.11.22@sha256:16b63af0e7342dd372da9ca989ea9fa542fc68f4640972d59a8450a5240fe42e /uv /uvx /bin/

# Set uv environment variables
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_NO_CACHE=1

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --frozen

# Create non-root user
RUN groupadd --gid 1001 mcp && \
    useradd --uid 1001 --gid mcp --no-create-home --shell /sbin/nologin mcp && \
    chown -R mcp:mcp /app

USER 1001

# Run the MCP server app
CMD ["uv", "run", "main.py"]
