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
            *)
                echo "❌ Unknown argument: $arg"
                echo "Usage: $0 [--format] [--lint] [--test]"
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
    echo "⏭️  mypy disabled for now"

    echo "🔒 Security scanning with bandit..."
    echo "⏭️ bandit disabled for now. You can run it manually with $PYTHON_CMD -m bandit -r . -f json -o bandit-report.json"
fi

# Run tests
if [ "$RUN_TEST" = true ]; then
    echo "🧪 Running tests..."
    $PYTHON_CMD -m pytest tests/ -v || {
        echo "❌ Tests failed"
        exit 1
    }
fi

echo "🎉 All checks passed! ✨"
