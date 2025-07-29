"""Data models and type definitions for the MCP server."""

# Import types explicitly to avoid import errors
from .types import (
    BuildInfo,
    DiagnosticResult,
    JobSpec,
    JobStatus,
    LogResult,
    PRInfo,
    ProwJob,
    TestFailure,
)
