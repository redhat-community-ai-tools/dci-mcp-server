"""Type definitions and data models for the MCP server."""

from dataclasses import dataclass
from typing import Any, TypedDict


class JobSpec(TypedDict, total=False):
    """Type definition for Prow job specification."""

    job: str
    refs: dict[str, Any]


class JobStatus(TypedDict, total=False):
    """Type definition for Prow job status."""

    state: str
    startTime: str
    completionTime: str
    url: str
    build_id: str


class ProwJob(TypedDict, total=False):
    """Type definition for a complete Prow job."""

    metadata: dict[str, Any]
    spec: JobSpec
    status: JobStatus


class PRInfo(TypedDict, total=False):
    """Type definition for PR information."""

    is_pr_job: bool
    org_repo: str | None
    pr_number: str | None


@dataclass
class BuildInfo:
    """Data class for build information."""

    build_id: str
    job_name: str
    pr_number: str | None = None
    org_repo: str | None = None
    build_url: str | None = None
    source: str | None = None
    confidence: str | None = None
    total_builds_found: int | None = None


@dataclass
class LogResult:
    """Data class for log retrieval results."""

    build_id: str
    job_name: str
    logs: str | None = None
    artifacts_url: str | None = None
    log_url_used: str | None = None
    error: str | None = None


@dataclass
class TestFailure:
    """Data class for test failure information."""

    test_name: str
    failure_message: str
    failure_details: str


class DiagnosticResult(TypedDict, total=False):
    """Type definition for diagnostic results."""

    pr_number: str
    org_repo: str
    job_name: str
    timestamp: str
    checks: dict[str, Any]
    recommendations: list[str]
    build_info: dict[str, Any]
    overall_status: str
    primary_recommendation: str
