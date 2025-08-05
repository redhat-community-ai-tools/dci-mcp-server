#!/bin/bash

# DCI MCP Server - Code Quality Checks
# This script runs all the code quality checks that would normally be run by pre-commit

set -e

echo "🔍 Running code quality checks..."

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Use the virtual environment Python
PYTHON_CMD="./.venv/bin/python"

# Function to run a check and report status
run_check() {
    local name="$1"
    local command="$2"
    
    echo "📋 Running $name..."
    if eval "$command"; then
        echo "✅ $name passed"
    else
        echo "❌ $name failed"
        return 1
    fi
}

# Run all checks
echo "🎨 Formatting code with Black..."
$PYTHON_CMD -m black --check --diff . || {
    echo "⚠️  Black found formatting issues. Run '$PYTHON_CMD -m black .' to fix them."
    exit 1
}

echo "📦 Sorting imports with isort..."
$PYTHON_CMD -m isort --check-only --diff . || {
    echo "⚠️  isort found import sorting issues. Run '$PYTHON_CMD -m isort .' to fix them."
    exit 1
}

echo "🔧 Linting with Ruff..."
$PYTHON_CMD -m ruff check . || {
    echo "⚠️  Ruff found linting issues. Run '$PYTHON_CMD -m ruff check --fix .' to fix them."
    exit 1
}

echo "🔍 Type checking with mypy..."
echo "⏭️  mypy disabled for now"

echo "🔒 Security scanning with bandit..."
echo "⏭️ bandit disabled for now. You can run it manually with $PYTHON_CMD -m bandit -r . -f json -o bandit-report.json"

echo "🧪 Running tests..."
$PYTHON_CMD -m pytest tests/ -v || {
    echo "❌ Tests failed"
    exit 1
}

echo "🎉 All checks passed! ✨" 