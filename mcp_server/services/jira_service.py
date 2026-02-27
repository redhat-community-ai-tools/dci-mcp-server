"""Jira service for ticket data collection."""

import os
from typing import Any

from jira import JIRA
from jira.exceptions import JIRAError


def _simplify_field_value(value: Any) -> Any:
    """Simplify a raw Jira field value for readability.

    Extracts human-readable values from Jira's nested resource objects
    while preserving simple types unchanged.
    """
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_simplify_field_value(item) for item in value]
    if isinstance(value, dict):
        if "displayName" in value:
            return value["displayName"]
        if "name" in value:
            return value["name"]
        if "value" in value:
            return value["value"]
        return {k: _simplify_field_value(v) for k, v in value.items()}
    return str(value)


class JiraService:
    """Service class for Jira API interactions."""

    def __init__(self):
        """Initialize Jira service with authentication."""
        self.jira_url = os.environ.get("JIRA_URL", "https://issues.redhat.com")
        self.jira_token = os.environ.get("JIRA_API_TOKEN")
        self.jira_email = os.environ.get("JIRA_EMAIL")

        if not self.jira_token:
            raise ValueError(
                "JIRA_API_TOKEN environment variable must be set. "
                "See documentation for setup instructions."
            )

        self.jira = JIRA(server=self.jira_url, token_auth=self.jira_token)
        self._field_map: dict[str, str] | None = None

    def _get_field_map(self) -> dict[str, str]:
        """Get field ID to name mapping, cached per instance."""
        if self._field_map is None:
            try:
                fields = self.jira.fields()
                self._field_map = {f["id"]: f["name"] for f in fields}
            except Exception:
                self._field_map = {}
        return self._field_map

    def get_ticket_data(
        self, ticket_key: str, max_comments: int = 10
    ) -> dict[str, Any]:
        """
        Get comprehensive ticket data including comments.

        Returns:
            Dictionary containing ticket data and comments
        """
        try:
            # Get the issue
            issue = self.jira.issue(ticket_key, expand="changelog")

            # Extract basic ticket information
            ticket_data = {
                "key": issue.key,
                "summary": issue.fields.summary,
                "description": issue.fields.description,
                "status": issue.fields.status.name,
                "priority": (
                    getattr(issue.fields.priority, "name", None)
                    if issue.fields.priority
                    else None
                ),
                "issue_type": issue.fields.issuetype.name,
                "assignee": (
                    getattr(issue.fields.assignee, "displayName", None)
                    if issue.fields.assignee
                    else None
                ),
                "reporter": (
                    getattr(issue.fields.reporter, "displayName", None)
                    if issue.fields.reporter
                    else None
                ),
                "created": issue.fields.created,
                "updated": issue.fields.updated,
                "resolution": (
                    getattr(issue.fields.resolution, "name", None)
                    if issue.fields.resolution
                    else None
                ),
                "labels": issue.fields.labels,
                "components": (
                    [comp.name for comp in issue.fields.components]
                    if issue.fields.components
                    else []
                ),
                "fix_versions": (
                    [version.name for version in issue.fields.fixVersions]
                    if issue.fields.fixVersions
                    else []
                ),
                "affected_versions": (
                    [version.name for version in issue.fields.versions]
                    if issue.fields.versions
                    else []
                ),
                "url": f"{self.jira_url}/browse/{issue.key}",
            }

            # Extract custom fields
            field_map = self._get_field_map()
            raw_fields = issue.raw.get("fields", {})
            custom_fields = {}
            for field_id, raw_value in raw_fields.items():
                if not field_id.startswith("customfield_"):
                    continue
                if raw_value is None:
                    continue
                field_name = field_map.get(field_id, field_id)
                custom_fields[field_name] = _simplify_field_value(raw_value)
            if custom_fields:
                ticket_data["custom_fields"] = custom_fields

            # Get comments
            comments = self._get_comments(issue, max_comments)
            ticket_data["comments"] = comments

            # Get changelog/history
            changelog = self._get_changelog(issue)
            ticket_data["changelog"] = changelog

            return ticket_data

        except JIRAError as e:
            raise Exception(f"Jira API error: {e.text}") from e
        except Exception as e:
            raise Exception(f"Error retrieving ticket {ticket_key}: {str(e)}") from e

    def _get_comments(self, issue: Any, max_comments: int) -> list[dict[str, Any]]:
        """Extract comments from the issue."""
        comments = []

        if hasattr(issue.fields, "comment") and issue.fields.comment:
            comment_list = issue.fields.comment.comments
            # Get the most recent comments (up to max_comments)
            recent_comments = (
                comment_list[-max_comments:]
                if len(comment_list) > max_comments
                else comment_list
            )

            for comment in recent_comments:
                comment_data = {
                    "id": comment.id,
                    "author": getattr(comment.author, "displayName", "Unknown"),
                    "body": comment.body,
                    "created": comment.created,
                    "updated": comment.updated,
                }
                comments.append(comment_data)

        return comments

    def _get_changelog(self, issue: Any) -> list[dict[str, Any]]:
        """Extract changelog/history from the issue."""
        changelog = []

        if hasattr(issue, "changelog") and issue.changelog:
            for history in issue.changelog.histories:
                author = getattr(history, "author", None)
                history_data = {
                    "author": (
                        getattr(author, "displayName", "Unknown")
                        if author
                        else "Unknown"
                    ),
                    "created": history.created,
                    "items": [],
                }

                for item in history.items:
                    item_data = {
                        "field": item.field,
                        "field_type": item.fieldtype,
                        "from_string": item.fromString,
                        "to_string": item.toString,
                    }
                    history_data["items"].append(item_data)

                changelog.append(history_data)

        return changelog

    def search_tickets(self, jql: str, max_results: int = 50) -> list[dict[str, Any]]:
        """
        Search for tickets using JQL (Jira Query Language).

        Returns:
            List of ticket data dictionaries
        """
        try:
            issues = self.jira.search_issues(jql, maxResults=max_results)
            tickets = []

            for issue in issues:
                ticket_data = {
                    "key": issue.key,
                    "summary": issue.fields.summary,
                    "status": issue.fields.status.name,
                    "assignee": (
                        getattr(issue.fields.assignee, "displayName", None)
                        if issue.fields.assignee
                        else None
                    ),
                    "created": issue.fields.created,
                    "updated": issue.fields.updated,
                    "url": f"{self.jira_url}/browse/{issue.key}",
                }
                tickets.append(ticket_data)

            return tickets

        except JIRAError as e:
            raise Exception(f"Jira search error: {e.text}") from e
        except Exception as e:
            raise Exception(f"Error searching tickets: {str(e)}") from e

    def get_project_info(self, project_key: str) -> dict[str, Any]:
        """
        Get project information.

        Returns:
            Dictionary containing project information
        """
        try:
            project = self.jira.project(project_key)
            return {
                "key": project.key,
                "name": project.name,
                "description": getattr(project, "description", None),
                "lead": (
                    getattr(project.lead, "displayName", None)
                    if hasattr(project, "lead")
                    else None
                ),
                "url": f"{self.jira_url}/browse/{project.key}",
            }
        except JIRAError as e:
            raise Exception(f"Jira project error: {e.text}") from e
        except Exception as e:
            raise Exception(f"Error retrieving project {project_key}: {str(e)}") from e
