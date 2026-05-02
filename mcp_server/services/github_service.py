"""GitHub service for searching issues and pull requests."""

import os
from datetime import UTC
from typing import Any

from github import Auth, Github
from github.GithubException import GithubException, RateLimitExceededException


class GitHubService:
    """Service class for GitHub API interactions."""

    def __init__(self):
        """Initialize GitHub service with authentication."""
        self.github_token = os.environ.get("GITHUB_TOKEN")

        if not self.github_token:
            raise ValueError(
                "GITHUB_TOKEN environment variable must be set. "
                "See documentation for setup instructions."
            )

        auth = Auth.Token(self.github_token)
        self.github = Github(auth=auth)

    def search_issues(
        self, query: str, max_results: int = 50, offset: int = 0
    ) -> dict[str, Any]:
        """
        Search for issues and pull requests using GitHub search query syntax.

        Args:
            query: GitHub search query string
            max_results: Maximum number of results to return
            offset: Number of results to skip for pagination

        Returns:
            Dictionary with total_count and items list
        """
        try:
            issues = self.github.search_issues(query=query)
            total_count = issues.totalCount
            results = []

            skipped = 0
            collected = 0
            for issue in issues:
                if skipped < offset:
                    skipped += 1
                    continue
                if collected >= max_results:
                    break

                issue_data = {
                    "number": issue.number,
                    "title": issue.title,
                    "body": issue.body,
                    "state": issue.state,
                    "locked": issue.locked,
                    "author_association": issue.author_association,
                    "comments": issue.comments,
                    "repository": issue.repository.full_name,
                    "type": "pull_request" if issue.pull_request else "issue",
                    "author": issue.user.login if issue.user else None,
                    "assignees": (
                        [assignee.login for assignee in issue.assignees]
                        if issue.assignees
                        else []
                    ),
                    "labels": [label.name for label in issue.labels]
                    if issue.labels
                    else [],
                    "milestone": issue.milestone.title if issue.milestone else None,
                    "created_at": issue.created_at.isoformat()
                    if issue.created_at
                    else None,
                    "updated_at": issue.updated_at.isoformat()
                    if issue.updated_at
                    else None,
                    "closed_at": issue.closed_at.isoformat()
                    if issue.closed_at
                    else None,
                    "merged_at": (
                        issue.pull_request.merged_at.isoformat()
                        if issue.pull_request and issue.pull_request.merged_at
                        else None
                    ),
                    "url": issue.html_url,
                }
                results.append(issue_data)
                collected += 1

            return {
                "total_count": total_count,
                "offset": offset,
                "limit": max_results,
                "items": results,
            }

        except RateLimitExceededException as e:
            raise Exception(self._format_rate_limit_error(e)) from e
        except GithubException as e:
            raise Exception(f"GitHub API error: {e.data.get('message', str(e))}") from e
        except Exception as e:
            raise Exception(f"Error searching GitHub: {str(e)}") from e

    def get_issue(
        self,
        repo_full_name: str,
        issue_number: int,
        max_comments: int = 10,
        comment_offset: int = 0,
    ) -> dict[str, Any]:
        """
        Get comprehensive issue/PR data including comments.

        Args:
            repo_full_name: Repository in owner/repo format
            issue_number: Issue or PR number
            max_comments: Maximum number of comments to return
            comment_offset: Number of comments to skip for pagination

        Returns:
            Dictionary containing issue/PR data
        """
        try:
            repo = self.github.get_repo(repo_full_name)
            issue = repo.get_issue(number=issue_number)

            issue_data = {
                "number": issue.number,
                "title": issue.title,
                "body": issue.body,
                "state": issue.state,
                "repository": repo_full_name,
                "type": "pull_request" if issue.pull_request else "issue",
                "author": issue.user.login if issue.user else None,
                "assignees": (
                    [assignee.login for assignee in issue.assignees]
                    if issue.assignees
                    else []
                ),
                "labels": [label.name for label in issue.labels]
                if issue.labels
                else [],
                "milestone": issue.milestone.title if issue.milestone else None,
                "created_at": issue.created_at.isoformat()
                if issue.created_at
                else None,
                "updated_at": issue.updated_at.isoformat()
                if issue.updated_at
                else None,
                "closed_at": issue.closed_at.isoformat() if issue.closed_at else None,
                "url": issue.html_url,
                "total_comments": issue.comments,
            }

            # Get comments
            comments = self._get_comments(issue, max_comments, comment_offset)
            issue_data["comments"] = comments

            # Get PR-specific data if it's a pull request
            if issue.pull_request:
                pr = repo.get_pull(number=issue_number)
                issue_data["pull_request_data"] = {
                    "merged": pr.merged,
                    "merged_at": pr.merged_at.isoformat() if pr.merged_at else None,
                    "merged_by": pr.merged_by.login if pr.merged_by else None,
                    "base_ref": pr.base.ref,
                    "head_ref": pr.head.ref,
                    "draft": pr.draft,
                    "additions": pr.additions,
                    "deletions": pr.deletions,
                    "changed_files": pr.changed_files,
                }

            return issue_data

        except RateLimitExceededException as e:
            raise Exception(self._format_rate_limit_error(e)) from e
        except GithubException as e:
            raise Exception(f"GitHub API error: {e.data.get('message', str(e))}") from e
        except Exception as e:
            raise Exception(
                f"Error retrieving issue {repo_full_name}#{issue_number}: {str(e)}"
            ) from e

    def get_pr_diff(
        self,
        repo_full_name: str,
        pull_number: int,
        max_files: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        Get the diff/patch for a pull request.

        Args:
            repo_full_name: Repository in owner/repo format
            pull_number: Pull request number
            max_files: Maximum number of files to return (default: 100)
            offset: Number of files to skip for pagination (default: 0)

        Returns:
            Dictionary containing PR summary and per-file diffs
        """
        try:
            repo = self.github.get_repo(repo_full_name)
            pr = repo.get_pull(number=pull_number)

            result: dict[str, Any] = {
                "number": pr.number,
                "title": pr.title,
                "state": pr.state,
                "merged": pr.merged,
                "base_ref": pr.base.ref,
                "head_ref": pr.head.ref,
                "additions": pr.additions,
                "deletions": pr.deletions,
                "changed_files": pr.changed_files,
                "url": pr.html_url,
            }

            files = []
            skipped = 0
            collected = 0
            for pr_file in pr.get_files():
                if skipped < offset:
                    skipped += 1
                    continue
                if collected >= max_files:
                    break
                file_data: dict[str, Any] = {
                    "filename": pr_file.filename,
                    "status": pr_file.status,
                    "additions": pr_file.additions,
                    "deletions": pr_file.deletions,
                    "changes": pr_file.changes,
                    "patch": pr_file.patch,
                    "sha": pr_file.sha,
                }
                if pr_file.previous_filename:
                    file_data["previous_filename"] = pr_file.previous_filename
                files.append(file_data)
                collected += 1

            result["files"] = files
            result["files_returned"] = len(files)
            result["offset"] = offset
            result["total_files"] = pr.changed_files
            if pr.changed_files > offset + max_files:
                result["truncated"] = True
                result["truncation_message"] = (
                    f"Showing {len(files)} of {pr.changed_files} files "
                    f"(offset: {offset}). "
                    f"Use offset and max_files parameters to paginate."
                )

            return result

        except RateLimitExceededException as e:
            raise Exception(self._format_rate_limit_error(e)) from e
        except GithubException as e:
            raise Exception(f"GitHub API error: {e.data.get('message', str(e))}") from e
        except Exception as e:
            raise Exception(
                f"Error retrieving PR diff {repo_full_name}#{pull_number}: {str(e)}"
            ) from e

    def get_pr_checks(self, repo_full_name: str, pull_number: int) -> dict[str, Any]:
        """Get CI check runs and commit statuses for a pull request."""
        try:
            repo = self.github.get_repo(repo_full_name)
            pr = repo.get_pull(number=pull_number)

            commit = repo.get_commit(pr.head.sha)

            check_runs_list = []
            for cr in commit.get_check_runs():
                check_runs_list.append(
                    {
                        "id": cr.id,
                        "name": cr.name,
                        "status": cr.status,
                        "conclusion": cr.conclusion,
                        "started_at": (
                            cr.started_at.isoformat() if cr.started_at else None
                        ),
                        "completed_at": (
                            cr.completed_at.isoformat() if cr.completed_at else None
                        ),
                        "html_url": cr.html_url,
                        "details_url": cr.details_url,
                    }
                )

            combined = commit.get_combined_status()
            commit_statuses = []
            for s in combined.statuses:
                commit_statuses.append(
                    {
                        "context": s.context,
                        "state": s.state,
                        "description": s.description,
                        "target_url": s.target_url,
                    }
                )

            return {
                "number": pr.number,
                "title": pr.title,
                "state": pr.state,
                "head_sha": pr.head.sha,
                "url": pr.html_url,
                "check_runs": check_runs_list,
                "total_check_runs": len(check_runs_list),
                "commit_statuses": commit_statuses,
                "combined_status": combined.state,
            }

        except RateLimitExceededException as e:
            raise Exception(self._format_rate_limit_error(e)) from e
        except GithubException as e:
            raise Exception(f"GitHub API error: {e.data.get('message', str(e))}") from e
        except Exception as e:
            raise Exception(
                f"Error retrieving PR checks {repo_full_name}#{pull_number}: {str(e)}"
            ) from e

    @staticmethod
    def _format_rate_limit_error(e: RateLimitExceededException) -> str:
        """Build an actionable error message from a rate limit exception."""
        reset_info = ""
        if e.headers:
            reset_ts = e.headers.get("x-ratelimit-reset")
            remaining = e.headers.get("x-ratelimit-remaining", "0")
            limit = e.headers.get("x-ratelimit-limit", "unknown")
            if reset_ts:
                from datetime import datetime

                reset_dt = datetime.fromtimestamp(int(reset_ts), tz=UTC)
                reset_info = (
                    f" Rate limit resets at {reset_dt.isoformat()} UTC."
                    f" ({remaining}/{limit} requests remaining)"
                )
        return (
            f"GitHub API rate limit exceeded.{reset_info}"
            " Please retry after the reset time."
        )

    def _get_comments(
        self, issue: Any, max_comments: int, offset: int = 0
    ) -> list[dict[str, Any]]:
        """Extract comments from the issue with pagination support."""
        comments = []

        try:
            all_comments = issue.get_comments()
            skipped = 0
            collected = 0
            for comment in all_comments:
                if skipped < offset:
                    skipped += 1
                    continue
                if collected >= max_comments:
                    break
                comment_data = {
                    "id": comment.id,
                    "author": comment.user.login if comment.user else None,
                    "body": comment.body,
                    "created_at": comment.created_at.isoformat()
                    if comment.created_at
                    else None,
                    "updated_at": comment.updated_at.isoformat()
                    if comment.updated_at
                    else None,
                }
                comments.append(comment_data)
                collected += 1

        except RateLimitExceededException:
            raise
        except Exception:
            pass

        return comments

    def get_repository_info(self, repo_full_name: str) -> dict[str, Any]:
        """
        Get repository information.

        Returns:
            Dictionary containing repository information
        """
        try:
            repo = self.github.get_repo(repo_full_name)
            return {
                "name": repo.name,
                "full_name": repo.full_name,
                "description": repo.description,
                "owner": repo.owner.login if repo.owner else None,
                "private": repo.private,
                "default_branch": repo.default_branch,
                "stars": repo.stargazers_count,
                "forks": repo.forks_count,
                "open_issues": repo.open_issues_count,
                "language": repo.language,
                "created_at": repo.created_at.isoformat() if repo.created_at else None,
                "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
                "url": repo.html_url,
            }
        except RateLimitExceededException as e:
            raise Exception(self._format_rate_limit_error(e)) from e
        except GithubException as e:
            raise Exception(f"GitHub API error: {e.data.get('message', str(e))}") from e
        except Exception as e:
            raise Exception(
                f"Error retrieving repository {repo_full_name}: {str(e)}"
            ) from e

    def get_rate_limit_status(self) -> dict[str, Any]:
        """
        Return current GitHub API rate limit status for core and search resources.

        Returns:
            Dictionary with rate limit info for 'core' and 'search' resources.
        """
        try:
            rl = self.github.get_rate_limit()
            core = rl.resources.core
            search = rl.resources.search
            return {
                "core": {
                    "limit": core.limit,
                    "remaining": core.remaining,
                    "used": core.used,
                    "reset": core.reset.isoformat() if core.reset else None,
                },
                "search": {
                    "limit": search.limit,
                    "remaining": search.remaining,
                    "used": search.used,
                    "reset": search.reset.isoformat() if search.reset else None,
                },
            }
        except RateLimitExceededException as e:
            raise Exception(self._format_rate_limit_error(e)) from e
        except GithubException as e:
            raise Exception(f"GitHub API error: {e.data.get('message', str(e))}") from e
        except Exception as e:
            raise Exception(f"Error retrieving rate limit status: {str(e)}") from e
