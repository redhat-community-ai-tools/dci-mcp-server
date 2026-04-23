"""GitLab service for interacting with projects, issues, and merge requests."""

import os
from typing import Any

from gitlab import Gitlab
from gitlab.exceptions import GitlabAuthenticationError, GitlabError


class GitLabService:
    """Service class for GitLab API interactions."""

    def __init__(
        self,
        gitlab_url: str | None = None,
        ssl_verify: bool | str | None = None,
    ):
        """Initialize GitLab service with authentication.

        Args:
            gitlab_url: GitLab instance URL. Overrides GITLAB_URL env var.
                        Defaults to GITLAB_URL or https://gitlab.com.
            ssl_verify: SSL verification. True/False or path to CA bundle.
                        Overrides GITLAB_SSL_VERIFY env var. Defaults to True.
        """
        self.gitlab_token = os.environ.get("GITLAB_TOKEN")
        self.gitlab_url = (
            gitlab_url or os.environ.get("GITLAB_URL") or "https://gitlab.com"
        )

        if ssl_verify is not None:
            self.ssl_verify = ssl_verify
        else:
            env_val = os.environ.get("GITLAB_SSL_VERIFY")
            if env_val is not None:
                if env_val.lower() in ("false", "0", "no"):
                    self.ssl_verify: bool | str = False
                elif env_val.lower() in ("true", "1", "yes"):
                    self.ssl_verify = True
                else:
                    self.ssl_verify = env_val
            else:
                self.ssl_verify = True

        if not self.gitlab_token:
            raise ValueError(
                "GITLAB_TOKEN environment variable must be set. "
                "See documentation for setup instructions."
            )

        self.gl = Gitlab(
            self.gitlab_url,
            private_token=self.gitlab_token,
            ssl_verify=self.ssl_verify,
        )

    def search_issues(
        self,
        project_path: str,
        search: str | None = None,
        state: str | None = None,
        labels: list[str] | None = None,
        max_results: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        Search for issues in a GitLab project.

        Args:
            project_path: Project path (group/project) or numeric ID
            search: Text search term
            state: Filter by state (opened, closed, all)
            labels: Filter by labels
            max_results: Maximum number of results to return
            offset: Number of results to skip for pagination

        Returns:
            Dictionary with total_count and items list
        """
        try:
            project = self.gl.projects.get(project_path)

            kwargs: dict[str, Any] = {
                "iterator": True,
                "per_page": 100,
                "order_by": "updated_at",
                "sort": "desc",
            }
            if search:
                kwargs["search"] = search
            if state:
                kwargs["state"] = state
            if labels:
                kwargs["labels"] = labels

            issues_iter = project.issues.list(**kwargs)

            results = []
            skipped = 0
            collected = 0
            for issue in issues_iter:
                if skipped < offset:
                    skipped += 1
                    continue
                if collected >= max_results:
                    break

                issue_data = self._format_issue(issue, project_path)
                results.append(issue_data)
                collected += 1

            total = getattr(issues_iter, "total", None)

            return {
                "total_count": total,
                "offset": offset,
                "limit": max_results,
                "items": results,
            }

        except GitlabAuthenticationError as e:
            raise Exception(f"GitLab authentication error: {str(e)}") from e
        except GitlabError as e:
            raise Exception(f"GitLab API error: {str(e)}") from e
        except Exception as e:
            raise Exception(f"Error searching GitLab issues: {str(e)}") from e

    def get_issue(
        self,
        project_path: str,
        issue_iid: int,
        max_notes: int = 10,
        note_offset: int = 0,
    ) -> dict[str, Any]:
        """
        Get comprehensive issue data including notes (comments).

        Args:
            project_path: Project path (group/project) or numeric ID
            issue_iid: Issue internal ID (the number shown in the UI)
            max_notes: Maximum number of notes to return
            note_offset: Number of notes to skip for pagination

        Returns:
            Dictionary containing issue data
        """
        try:
            project = self.gl.projects.get(project_path)
            issue = project.issues.get(issue_iid)

            issue_data = self._format_issue(issue, project_path)
            issue_data["description"] = issue.description

            notes = self._get_notes(issue, max_notes, note_offset)
            issue_data["notes"] = notes

            return issue_data

        except GitlabAuthenticationError as e:
            raise Exception(f"GitLab authentication error: {str(e)}") from e
        except GitlabError as e:
            raise Exception(f"GitLab API error: {str(e)}") from e
        except Exception as e:
            raise Exception(
                f"Error retrieving issue {project_path}#{issue_iid}: {str(e)}"
            ) from e

    def search_merge_requests(
        self,
        project_path: str,
        search: str | None = None,
        state: str | None = None,
        labels: list[str] | None = None,
        max_results: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        Search for merge requests in a GitLab project.

        Args:
            project_path: Project path (group/project) or numeric ID
            search: Text search term
            state: Filter by state (opened, closed, merged, all)
            labels: Filter by labels
            max_results: Maximum number of results to return
            offset: Number of results to skip for pagination

        Returns:
            Dictionary with total_count and items list
        """
        try:
            project = self.gl.projects.get(project_path)

            kwargs: dict[str, Any] = {
                "iterator": True,
                "per_page": 100,
                "order_by": "updated_at",
                "sort": "desc",
            }
            if search:
                kwargs["search"] = search
            if state:
                kwargs["state"] = state
            if labels:
                kwargs["labels"] = labels

            mrs_iter = project.mergerequests.list(**kwargs)

            results = []
            skipped = 0
            collected = 0
            for mr in mrs_iter:
                if skipped < offset:
                    skipped += 1
                    continue
                if collected >= max_results:
                    break

                mr_data = {
                    "iid": mr.iid,
                    "title": mr.title,
                    "state": mr.state,
                    "draft": getattr(mr, "draft", False),
                    "project": project_path,
                    "author": (mr.author.get("username") if mr.author else None),
                    "assignees": (
                        [a.get("username") for a in mr.assignees]
                        if mr.assignees
                        else []
                    ),
                    "reviewers": (
                        [r.get("username") for r in mr.reviewers]
                        if getattr(mr, "reviewers", None)
                        else []
                    ),
                    "labels": mr.labels if mr.labels else [],
                    "milestone": (mr.milestone.get("title") if mr.milestone else None),
                    "source_branch": mr.source_branch,
                    "target_branch": mr.target_branch,
                    "merge_status": getattr(mr, "merge_status", None),
                    "has_conflicts": getattr(mr, "has_conflicts", None),
                    "created_at": mr.created_at,
                    "updated_at": mr.updated_at,
                    "merged_at": getattr(mr, "merged_at", None),
                    "closed_at": getattr(mr, "closed_at", None),
                    "url": mr.web_url,
                }
                results.append(mr_data)
                collected += 1

            total = getattr(mrs_iter, "total", None)

            return {
                "total_count": total,
                "offset": offset,
                "limit": max_results,
                "items": results,
            }

        except GitlabAuthenticationError as e:
            raise Exception(f"GitLab authentication error: {str(e)}") from e
        except GitlabError as e:
            raise Exception(f"GitLab API error: {str(e)}") from e
        except Exception as e:
            raise Exception(f"Error searching GitLab merge requests: {str(e)}") from e

    def get_mr_diff(
        self,
        project_path: str,
        mr_iid: int,
        max_files: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        Get the diff/patch for a merge request.

        Args:
            project_path: Project path (group/project) or numeric ID
            mr_iid: Merge request internal ID
            max_files: Maximum number of files to return (default: 100)
            offset: Number of files to skip for pagination (default: 0)

        Returns:
            Dictionary containing MR summary and per-file diffs
        """
        try:
            project = self.gl.projects.get(project_path)
            mr = project.mergerequests.get(mr_iid)

            changes_data = mr.changes()
            file_changes = changes_data.get("changes", [])
            total_files = len(file_changes)

            total_additions = 0
            total_deletions = 0

            result: dict[str, Any] = {
                "iid": mr.iid,
                "title": mr.title,
                "state": mr.state,
                "draft": getattr(mr, "draft", False),
                "merged_at": getattr(mr, "merged_at", None),
                "source_branch": mr.source_branch,
                "target_branch": mr.target_branch,
                "url": mr.web_url,
            }

            files = []
            skipped = 0
            collected = 0
            for change in file_changes:
                additions, deletions = self._count_diff_stats(change.get("diff"))
                total_additions += additions
                total_deletions += deletions

                if skipped < offset:
                    skipped += 1
                    continue
                if collected >= max_files:
                    continue

                file_data: dict[str, Any] = {
                    "filename": change.get("new_path"),
                    "status": self._get_change_status(change),
                    "additions": additions,
                    "deletions": deletions,
                    "diff": change.get("diff"),
                }
                if change.get("renamed_file") and change.get("old_path") != change.get(
                    "new_path"
                ):
                    file_data["old_filename"] = change.get("old_path")
                files.append(file_data)
                collected += 1

            result["additions"] = total_additions
            result["deletions"] = total_deletions
            result["changed_files"] = total_files
            result["files"] = files
            result["files_returned"] = len(files)
            result["offset"] = offset
            result["total_files"] = total_files
            if total_files > offset + max_files:
                result["truncated"] = True
                result["truncation_message"] = (
                    f"Showing {len(files)} of {total_files} files "
                    f"(offset: {offset}). "
                    f"Use offset and max_files parameters to paginate."
                )

            return result

        except GitlabAuthenticationError as e:
            raise Exception(f"GitLab authentication error: {str(e)}") from e
        except GitlabError as e:
            raise Exception(f"GitLab API error: {str(e)}") from e
        except Exception as e:
            raise Exception(
                f"Error retrieving MR diff {project_path}!{mr_iid}: {str(e)}"
            ) from e

    def get_project_info(self, project_path: str) -> dict[str, Any]:
        """
        Get project information.

        Returns:
            Dictionary containing project information
        """
        try:
            project = self.gl.projects.get(project_path)
            return {
                "name": project.name,
                "path_with_namespace": project.path_with_namespace,
                "description": project.description,
                "namespace": (
                    project.namespace.get("full_path") if project.namespace else None
                ),
                "visibility": project.visibility,
                "default_branch": getattr(project, "default_branch", None),
                "stars": project.star_count,
                "forks": project.forks_count,
                "open_issues_count": getattr(project, "open_issues_count", None),
                "topics": getattr(project, "topics", []),
                "created_at": project.created_at,
                "last_activity_at": getattr(project, "last_activity_at", None),
                "url": project.web_url,
            }
        except GitlabAuthenticationError as e:
            raise Exception(f"GitLab authentication error: {str(e)}") from e
        except GitlabError as e:
            raise Exception(f"GitLab API error: {str(e)}") from e
        except Exception as e:
            raise Exception(f"Error retrieving project {project_path}: {str(e)}") from e

    def _format_issue(self, issue: Any, project_path: str) -> dict[str, Any]:
        """Format an issue object into a standardized dictionary."""
        return {
            "iid": issue.iid,
            "title": issue.title,
            "state": issue.state,
            "confidential": getattr(issue, "confidential", False),
            "project": project_path,
            "author": (issue.author.get("username") if issue.author else None),
            "assignees": (
                [a.get("username") for a in issue.assignees] if issue.assignees else []
            ),
            "labels": issue.labels if issue.labels else [],
            "milestone": (issue.milestone.get("title") if issue.milestone else None),
            "created_at": issue.created_at,
            "updated_at": issue.updated_at,
            "closed_at": getattr(issue, "closed_at", None),
            "url": issue.web_url,
            "total_notes": getattr(issue, "user_notes_count", 0),
        }

    def _get_notes(
        self, issue: Any, max_notes: int, offset: int = 0
    ) -> list[dict[str, Any]]:
        """Extract notes (comments) from an issue with pagination support."""
        notes = []

        try:
            all_notes = issue.notes.list(iterator=True, per_page=100, sort="asc")
            skipped = 0
            collected = 0
            for note in all_notes:
                if getattr(note, "system", False):
                    continue
                if skipped < offset:
                    skipped += 1
                    continue
                if collected >= max_notes:
                    break
                note_data = {
                    "id": note.id,
                    "author": (note.author.get("username") if note.author else None),
                    "body": note.body,
                    "created_at": note.created_at,
                    "updated_at": note.updated_at,
                }
                notes.append(note_data)
                collected += 1

        except GitlabAuthenticationError:
            raise
        except Exception:
            pass

        return notes

    @staticmethod
    def _get_change_status(change: dict[str, Any]) -> str:
        """Determine the status of a file change."""
        if change.get("new_file"):
            return "added"
        elif change.get("deleted_file"):
            return "removed"
        elif change.get("renamed_file"):
            return "renamed"
        return "modified"

    @staticmethod
    def _count_diff_stats(diff_text: str | None) -> tuple[int, int]:
        """Count additions and deletions from a unified diff."""
        if not diff_text:
            return 0, 0
        additions = 0
        deletions = 0
        for line in diff_text.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                additions += 1
            elif line.startswith("-") and not line.startswith("---"):
                deletions += 1
        return additions, deletions
