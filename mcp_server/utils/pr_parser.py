"""Utilities for parsing PR information from job specifications and names."""

from typing import Any


def extract_pr_info(
    job_spec: dict[str, Any] | None, job_name: str | None = None
) -> tuple[bool, str | None, str | None]:
    """Extract PR information from job spec or job name.

    Args:
        job_spec: The job specification dictionary
        job_name: Optional job name for fallback parsing

    Returns:
        tuple: (is_pr_job, org_repo, pr_number) or (False, None, None)
    """
    try:
        # First, try to extract from job spec if available
        if job_spec:
            refs = job_spec.get("refs", {})
            if refs.get("pulls"):
                # This is a PR job
                org = refs.get("org", "")
                repo = refs.get("repo", "")
                pulls = refs.get("pulls", [])

                if pulls and org and repo:
                    pr_number = str(pulls[0].get("number", ""))
                    org_repo = f"{org}_{repo}"
                    return True, org_repo, pr_number

        # Fallback: try to detect PR job from job name pattern
        if job_name and "pull-ci-" in job_name:
            # Pattern: pull-ci-{org}-{repo}-{branch}-{test-name}
            # Example: pull-ci-redhat-developer-rhdh-main-e2e-tests
            parts = job_name.split("-")
            if len(parts) >= 5 and parts[0] == "pull" and parts[1] == "ci":
                # Try to extract org and repo
                # This is a heuristic and may need adjustment for specific patterns
                org = parts[2]
                repo = parts[3]
                if org and repo:
                    org_repo = f"{org}_{repo}"
                    # We can't determine PR number from job name alone
                    # This will require getting it from the actual file paths available
                    return True, org_repo, None
    except Exception:
        pass

    return False, None, None
