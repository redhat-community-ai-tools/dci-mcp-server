"""Configuration constants for the MCP DCI server."""

import os
import sys
from pathlib import Path

# Load environment variables from .env file if it exists
from dotenv import load_dotenv

# Look for .env file in the project root
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"

load_dotenv(env_file, verbose=True, override=True)

# HTTP client configuration
DEFAULT_TIMEOUT = 30.0


def validate_required_config() -> bool:
    """Validate that DCI authentication is configured."""
    # set DCI_CS_URL=https://api.distributed-ci.io in the environment if not set
    if "DCI_CS_URL" not in os.environ:
        os.environ["DCI_CS_URL"] = "https://api.distributed-ci.io"

    print(
        f"Validating DCI authentication configuration...from {env_file}",
        file=sys.stderr,
    )
    # Check for DCI authentication
    if ("DCI_CLIENT_ID" in os.environ and "DCI_API_SECRET" in os.environ) or (
        "DCI_LOGIN" in os.environ and "DCI_PASSWORD" in os.environ
    ):
        return True

    print(
        "WARNING: DCI authentication not configured. Set either DCI_CLIENT_ID+DCI_API_SECRET or "
        "DCI_LOGIN+DCI_PASSWORD",
        file=sys.stderr,
    )
    print(
        "You can create a .env file in the project root with your DCI credentials:",
        file=sys.stderr,
    )
    print("DCI_CLIENT_ID=your-dci-ckient-id", file=sys.stderr)
    print("DCI_API_SECRET=your-dci-api-secret", file=sys.stderr)
    print("# OR", file=sys.stderr)
    print("DCI_LOGIN=your-login", file=sys.stderr)
    print("DCI_PASSWORD=your-passwod", file=sys.stderr)
    return False


def validate_google_drive_config() -> bool:
    """Validate that Google Drive authentication is configured."""
    credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
    credentials_file = Path(credentials_path)

    if credentials_file.exists():
        return True

    print(
        "WARNING: Google Drive authentication not configured.",
        file=sys.stderr,
    )
    print(
        "To use Google Drive features, you need to:",
        file=sys.stderr,
    )
    print(
        "1. Go to Google Cloud Console (https://console.cloud.google.com/)",
        file=sys.stderr,
    )
    print("2. Create a new project or select an existing one", file=sys.stderr)
    print("3. Enable the Google Drive API", file=sys.stderr)
    print("4. Create OAuth 2.0 credentials (Desktop application)", file=sys.stderr)
    print("5. Download the credentials JSON file", file=sys.stderr)
    print("6. Save it as 'credentials.json' in the project root", file=sys.stderr)
    print("7. Or set GOOGLE_CREDENTIALS_PATH environment variable", file=sys.stderr)
    print("", file=sys.stderr)
    print("Optional environment variables:", file=sys.stderr)
    print("GOOGLE_CREDENTIALS_PATH=path/to/credentials.json", file=sys.stderr)
    print("GOOGLE_TOKEN_PATH=path/to/token.json", file=sys.stderr)

    return False
