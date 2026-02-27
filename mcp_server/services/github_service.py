"""GitHub service for searching issues and pull requests."""

import os
from typing import Any

from github import Auth, Github
from github.GithubException import GithubException


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

    def search_issues(self, query: str, max_results: int = 50) -> list[dict[str, Any]]:
        """
        Search for issues and pull requests using GitHub search query syntax.

        Returns:
            List of issue/PR data dictionaries
        """
        try:
            issues = self.github.search_issues(query=query)
            results = []

            # Limit results to max_results
            count = 0
            for issue in issues:
                if count >= max_results:
                    break

                issue_data = {
                    "number": issue.number,
                    "title": issue.title,
                    "state": issue.state,
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
                    "created_at": issue.created_at.isoformat()
                    if issue.created_at
                    else None,
                    "updated_at": issue.updated_at.isoformat()
                    if issue.updated_at
                    else None,
                    "closed_at": issue.closed_at.isoformat()
                    if issue.closed_at
                    else None,
                    "url": issue.html_url,
                }
                results.append(issue_data)
                count += 1

            return results

        except GithubException as e:
            raise Exception(f"GitHub API error: {e.data.get('message', str(e))}") from e
        except Exception as e:
            raise Exception(f"Error searching GitHub: {str(e)}") from e

    def get_issue(
        self, repo_full_name: str, issue_number: int, max_comments: int = 10
    ) -> dict[str, Any]:
        """
        Get comprehensive issue/PR data including comments.

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
            }

            # Get comments
            comments = self._get_comments(issue, max_comments)
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
    ) -> dict[str, Any]:
        """
        Get the diff/patch for a pull request.

        Args:
            repo_full_name: Repository in owner/repo format
            pull_number: Pull request number
            max_files: Maximum number of files to return (default: 100)

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
            count = 0
            for pr_file in pr.get_files():
                if count >= max_files:
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
                count += 1

            result["files"] = files
            result["files_returned"] = len(files)
            result["total_files"] = pr.changed_files
            if pr.changed_files > max_files:
                result["truncated"] = True
                result["truncation_message"] = (
                    f"Showing {max_files} of {pr.changed_files} files. "
                    f"Use max_files parameter to retrieve more."
                )

            return result

        except GithubException as e:
            raise Exception(f"GitHub API error: {e.data.get('message', str(e))}") from e
        except Exception as e:
            raise Exception(
                f"Error retrieving PR diff {repo_full_name}#{pull_number}: {str(e)}"
            ) from e

    def _get_comments(self, issue: Any, max_comments: int) -> list[dict[str, Any]]:
        """Extract comments from the issue."""
        comments = []

        try:
            all_comments = list(issue.get_comments())
            # Get the most recent comments (up to max_comments)
            recent_comments = (
                all_comments[-max_comments:]
                if len(all_comments) > max_comments
                else all_comments
            )

            for comment in recent_comments:
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

        except Exception:
            # If we can't get comments, just return empty list
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
        except GithubException as e:
            raise Exception(f"GitHub API error: {e.data.get('message', str(e))}") from e
        except Exception as e:
            raise Exception(
                f"Error retrieving repository {repo_full_name}: {str(e)}"
            ) from e
