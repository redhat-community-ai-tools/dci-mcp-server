#!/bin/bash

# DCI MCP Server - Code Quality Checks
# This script runs code quality checks that would normally be run by pre-commit
#
# Usage:
#   bash scripts/run-checks.sh          # Run all checks
#   bash scripts/run-checks.sh --format  # Run formatting checks only
#   bash scripts/run-checks.sh --lint    # Run linting checks only
#   bash scripts/run-checks.sh --test    # Run tests only
#   bash scripts/run-checks.sh --format --lint  # Run formatting and linting
#   bash scripts/run-checks.sh --container       # Build and smoke-test container images

set -e

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Use the virtual environment Python
PYTHON_CMD="./.venv/bin/python"

# Parse arguments
RUN_FORMAT=false
RUN_LINT=false
RUN_TEST=false
RUN_CONTAINER=false

if [ $# -eq 0 ]; then
    # No arguments: run all checks
    RUN_FORMAT=true
    RUN_LINT=true
    RUN_TEST=true
else
    for arg in "$@"; do
        case $arg in
            --format)
                RUN_FORMAT=true
                ;;
            --lint)
                RUN_LINT=true
                ;;
            --test)
                RUN_TEST=true
                ;;
            --container)
                RUN_CONTAINER=true
                ;;
            *)
                echo "❌ Unknown argument: $arg"
                echo "Usage: $0 [--format] [--lint] [--test] [--container]"
                exit 1
                ;;
        esac
    done
fi

echo "🔍 Running code quality checks..."

# Run formatting checks
if [ "$RUN_FORMAT" = true ]; then
    echo "🎨 Formatting code with Ruff format..."
    $PYTHON_CMD -m ruff format --check . || {
        echo "⚠️  Ruff format found formatting issues. Run '$PYTHON_CMD -m ruff format .' to fix them."
        exit 1
    }

    echo "📦 Sorting imports with isort..."
    $PYTHON_CMD -m isort --check-only --diff . || {
        echo "⚠️  isort found import sorting issues. Run '$PYTHON_CMD -m isort .' to fix them."
        exit 1
    }
fi

# Run linting checks
if [ "$RUN_LINT" = true ]; then
    echo "🔧 Linting with Ruff..."
    $PYTHON_CMD -m ruff check . || {
        echo "⚠️  Ruff found linting issues. Run '$PYTHON_CMD -m ruff check --fix .' to fix them."
        exit 1
    }

    echo "🔍 Type checking with mypy..."
    $PYTHON_CMD -m mypy mcp_server/ || {
        echo "⚠️  mypy found type errors. Fix them before committing."
        exit 1
    }

    echo "🔒 Security scanning with bandit..."
    $PYTHON_CMD -m bandit -r mcp_server/ -c pyproject.toml || {
        echo "⚠️  bandit found security issues. Fix them before committing."
        exit 1
    }
fi

# Run tests
if [ "$RUN_TEST" = true ]; then
    echo "🤖 Running eval tests (parallel)..."
    $PYTHON_CMD -m pytest tests/ -v -m "eval" -n auto || {
        echo "❌ Eval tests failed"
        exit 1
    }
    echo "🧪 Running tests..."
    $PYTHON_CMD -m pytest tests/ -v -m "not eval" || {
        echo "❌ Tests failed"
        exit 1
    }
fi

# Run container build and smoke test
if [ "$RUN_CONTAINER" = true ]; then
    if command -v podman &> /dev/null; then
        CONTAINER_CMD="podman"
    elif command -v docker &> /dev/null; then
        CONTAINER_CMD="docker"
    else
        echo "❌ Neither podman nor docker found. Install one to run container checks."
        exit 1
    fi

    SMOKE_TEST='uv run python -c "from mcp_server.main import create_server; s = create_server(); print(s.name)"'

    echo "🐳 Building container image (stdio)..."
    $CONTAINER_CMD build -t dci-mcp-server-test -f Containerfile . || {
        echo "❌ Container build failed (stdio)"
        exit 1
    }
    echo "🔬 Smoke-testing container image (stdio)..."
    $CONTAINER_CMD run --rm dci-mcp-server-test sh -c "$SMOKE_TEST" || {
        echo "❌ Container smoke test failed (stdio)"
        exit 1
    }

    echo "🐳 Building container image (SSE)..."
    $CONTAINER_CMD build -t dci-mcp-server-sse-test -f Containerfile.sse . || {
        echo "❌ Container build failed (SSE)"
        exit 1
    }
    echo "🔬 Smoke-testing container image (SSE)..."
    $CONTAINER_CMD run --rm dci-mcp-server-sse-test sh -c "$SMOKE_TEST" || {
        echo "❌ Container smoke test failed (SSE)"
        exit 1
    }

    echo "🧹 Cleaning up test images..."
    $CONTAINER_CMD rmi dci-mcp-server-test dci-mcp-server-sse-test 2>/dev/null || true
fi

echo "🎉 All checks passed! ✨"
