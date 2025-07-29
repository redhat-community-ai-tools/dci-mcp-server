#!/usr/bin/env python3
"""
Test runner for the MCP Prow server.
This script can run tests even if pytest is not globally installed.
"""

import os
import subprocess
import sys
from pathlib import Path


def install_dependencies():
    """Install test dependencies if not available."""
    try:
        # Check if pytest is available
        import importlib.util

        if importlib.util.find_spec("pytest") and importlib.util.find_spec(
            "pytest_asyncio"
        ):
            print("✓ Test dependencies already installed")
            return True
        else:
            print("Installing test dependencies...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "pytest", "pytest-asyncio"],
                check=True,
            )
            print("✓ Test dependencies installed successfully")
            return True
    except Exception as e:
        print(f"Error installing test dependencies: {e}")
        return False


def run_basic_tests():
    """Run basic function tests without pytest."""
    print("Running basic tests without pytest...")

    # Add current directory to path for imports
    sys.path.insert(0, str(Path(__file__).parent))

    try:
        from mcp_server.utils.pr_parser import extract_pr_info
        from mcp_server.utils.url_builder import construct_log_urls

        # Test 1: extract_pr_info with valid job spec
        job_spec = {
            "refs": {
                "pulls": [{"number": 1234}],
                "org": "test-org",
                "repo": "test-repo",
            }
        }
        is_pr, org_repo, pr_number = extract_pr_info(job_spec)
        assert is_pr is True
        assert org_repo == "test-org_test-repo"
        assert pr_number == "1234"
        print("✓ Test 1 passed: extract_pr_info with valid job spec")

        # Test 2: extract_pr_info with job name
        job_name = "pull-ci-redhat-developer-rhdh-main-e2e-tests"
        is_pr, org_repo, pr_number = extract_pr_info(None, job_name)
        assert is_pr is True
        assert org_repo == "redhat_developer"
        assert pr_number is None
        print("✓ Test 2 passed: extract_pr_info with job name")

        # Test 3: construct_log_urls for PR job
        artifacts_url, log_urls, pr_info = construct_log_urls(
            job_name, "build-123", job_spec
        )
        assert "pr-logs" in str(log_urls)
        assert "test-org_test-repo" in str(log_urls)
        print("✓ Test 3 passed: construct_log_urls for PR job")

        # Test 4: extract_pr_info with empty inputs
        is_pr, org_repo, pr_number = extract_pr_info(None, None)
        assert is_pr is False
        assert org_repo is None
        assert pr_number is None
        print("✓ Test 4 passed: extract_pr_info with empty inputs")

        print("\n🎉 All basic tests passed!")
        return True

    except Exception as e:
        print(f"✗ Basic test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def run_pytest_tests():
    """Run the full test suite using pytest."""
    print("Running full test suite with pytest...")

    try:
        # Try to run pytest with the tests directory
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_refactored.py",
                "-v",
                "--tb=short",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print("✓ All pytest tests passed!")
            print("\nTest output:")
            print(result.stdout)
            return True
        else:
            print("✗ Some pytest tests failed:")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False

    except FileNotFoundError:
        print("pytest not found, falling back to basic tests")
        return run_basic_tests()
    except Exception as e:
        print(f"Error running pytest: {e}")
        return run_basic_tests()


def show_test_summary():
    """Show a summary of the test structure."""
    print("\n" + "=" * 60)
    print("TEST STRUCTURE SUMMARY")
    print("=" * 60)
    print()
    print("✓ Test organization:")
    print("  - run_tests.py            # Main test runner (root level)")
    print("  - tests/                  # Test package directory")
    print("    ├── __init__.py         # Package initialization")
    print("    ├── test_refactored.py  # Comprehensive test suite")
    print("    └── legacy_tests.py     # Legacy tests (ignored)")
    print("  - pytest.ini             # Pytest configuration")
    print()
    print("✓ Test coverage:")
    print("  - 18 comprehensive tests covering all components")
    print("  - Utility functions, service layer, and MCP tools")
    print("  - Integration and end-to-end testing")
    print("  - Fast execution (under 0.25 seconds)")
    print()
    print("✓ Running tests:")
    print("  uv run python run_tests.py   # Main test runner (this file)")
    print("  uv run pytest tests/         # Direct pytest on tests directory")
    print("  uv run pytest                # Pytest auto-discovery")


def main():
    """Main test runner function."""
    print("MCP Server Test Suite Runner")
    print("=" * 40)
    print()

    # Check if we're in the right directory
    if not os.path.exists("mcp_server"):
        print(
            "✗ Error: mcp_server package not found. Please run from the project root."
        )
        return False

    # Try to install dependencies first
    deps_ok = install_dependencies()

    if deps_ok:
        # Try running with pytest first
        success = run_pytest_tests()
    else:
        # Fall back to basic tests
        success = run_basic_tests()

    # Show summary
    show_test_summary()

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
