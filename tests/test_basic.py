"""
Basic tests for the DCI MCP Server.
"""

import pytest


def test_imports():
    """Test that we can import the main modules."""
    try:
        import mcp_server.main

        # Test that the module is actually importable
        assert mcp_server.main is not None
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import required modules: {e}")


def test_config_functions():
    """Test that config functions exist and are callable."""
    from mcp_server.config import get_dci_api_key, get_dci_user_id, get_dci_user_secret

    # These should not raise exceptions even if env vars are not set
    get_dci_api_key()
    get_dci_user_id()
    get_dci_user_secret()


def test_basic_functionality():
    """Test basic functionality."""
    # This is a placeholder test that always passes
    assert True
