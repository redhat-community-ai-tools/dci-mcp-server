"""Configuration constants for the MCP DCI server."""

import os
import sys
from pathlib import Path

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv

    # Look for .env file in the project root
    project_root = Path(__file__).parent
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
    else:
        # Also try loading from current directory
        load_dotenv()
except ImportError:
    # dotenv not installed, continue without it
    pass

# DCI API URL
DCI_CS_URL = "https://api.distributed-ci.io"

# HTTP client configuration
DEFAULT_TIMEOUT = 30.0
EXTENDED_TIMEOUT = 60.0


# DCI API configuration
def get_dci_api_key() -> str | None:
    """Get DCI API key from environment, returning None if not set or is placeholder."""
    api_key = os.environ.get("DCI_API_KEY")
    if api_key and api_key != "your-dci-api-key":  # Ignore placeholder values
        return api_key
    return None


def get_dci_user_id() -> str | None:
    """Get DCI user ID from environment."""
    return os.environ.get("DCI_USER_ID")


def get_dci_user_secret() -> str | None:
    """Get DCI user secret from environment."""
    return os.environ.get("DCI_USER_SECRET")


def validate_required_config() -> None:
    """Validate that DCI authentication is configured."""
    # Check for DCI authentication
    if not get_dci_api_key() and not (get_dci_user_id() and get_dci_user_secret()):
        print(
            "WARNING: DCI authentication not configured. Set either DCI_API_KEY or "
            "DCI_USER_ID+DCI_USER_SECRET",
            file=sys.stderr,
        )
        print(
            "You can create a .env file in the project root with your DCI credentials:",
            file=sys.stderr,
        )
        print("DCI_API_KEY=your-dci-api-key", file=sys.stderr)
        print("# OR", file=sys.stderr)
        print("DCI_USER_ID=your-dci-user-id", file=sys.stderr)
        print("DCI_USER_SECRET=your-dci-user-secret", file=sys.stderr)
