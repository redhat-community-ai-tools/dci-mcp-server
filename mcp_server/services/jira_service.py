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
        """Initialize Jira service with authentication.

        Supports both Atlassian Cloud (basic auth with email + API token)
        and on-prem Jira Data Center (PAT bearer token).
        """
        self.jira_url = os.environ.get("JIRA_URL", "https://redhat.atlassian.net")
        self.jira_token = os.environ.get("JIRA_API_TOKEN")
        self.jira_email = os.environ.get("JIRA_EMAIL")

        if not self.jira_token:
            raise ValueError(
                "JIRA_API_TOKEN environment variable must be set. "
                "See documentation for setup instructions."
            )

        is_cloud = "atlassian.net" in self.jira_url
        if is_cloud and self.jira_email:
            self.jira = JIRA(
                server=self.jira_url,
                basic_auth=(self.jira_email, self.jira_token),
            )
        else:
            self.jira = JIRA(server=self.jira_url, token_auth=self.jira_token)
        self._field_map: dict[str, str] | None = None
        self._status_name_map: dict[str, str] | None = None

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
                "status": self._status_name(issue.fields.status),
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

    def _get_status_name_map(self) -> dict[str, str]:
        """Fetch status ID → English name map from Jira REST API v3.

        The v2 API (used by the jira library) returns localised status names.
        The v3 API includes ``untranslatedName`` which is always English.
        Result is cached per instance.
        """
        if self._status_name_map is not None:
            return self._status_name_map
        try:
            resp = self.jira._session.get(f"{self.jira_url}/rest/api/3/status")
            self._status_name_map = {
                s["id"]: s.get("untranslatedName") or s["name"] for s in resp.json()
            }
        except Exception:
            self._status_name_map = {}
        return self._status_name_map

    def _status_name(self, status_obj: Any) -> str:
        """Return the English status name, looked up from the v3 status map."""
        return self._get_status_name_map().get(status_obj.id) or status_obj.name

    def create_issue(
        self,
        project_key: str,
        summary: str,
        description: str | None = None,
        issue_type: str = "Task",
        priority: str | None = None,
        labels: list[str] | None = None,
        components: list[str] | None = None,
        assignee: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new Jira issue.

        Returns:
            Dictionary with created issue key, summary, and URL
        """
        try:
            fields: dict[str, Any] = {
                "project": {"key": project_key},
                "summary": summary,
                "issuetype": {"name": issue_type},
            }
            if description is not None:
                fields["description"] = description
            if priority is not None:
                fields["priority"] = {"name": priority}
            if labels is not None:
                fields["labels"] = labels
            if components is not None:
                fields["components"] = [{"name": c} for c in components]
            if assignee is not None:
                fields["assignee"] = {"name": assignee}

            issue = self.jira.create_issue(fields=fields)
            return {
                "key": issue.key,
                "summary": issue.fields.summary,
                "url": f"{self.jira_url}/browse/{issue.key}",
            }
        except JIRAError as e:
            raise Exception(f"Jira API error: {e.text}") from e
        except Exception as e:
            raise Exception(f"Error creating issue: {str(e)}") from e

    def update_issue(
        self,
        ticket_key: str,
        summary: str | None = None,
        description: str | None = None,
        priority: str | None = None,
        labels: list[str] | None = None,
        components: list[str] | None = None,
        assignee: str | None = None,
        transition: str | None = None,
    ) -> dict[str, Any]:
        """
        Update an existing Jira issue.

        Returns:
            Dictionary with updated issue information
        """
        try:
            issue = self.jira.issue(ticket_key)

            # Build field updates
            fields: dict[str, Any] = {}
            if summary is not None:
                fields["summary"] = summary
            if description is not None:
                fields["description"] = description
            if priority is not None:
                fields["priority"] = {"name": priority}
            if labels is not None:
                fields["labels"] = labels
            if components is not None:
                fields["components"] = [{"name": c} for c in components]
            if assignee is not None:
                fields["assignee"] = {"name": assignee}

            if fields:
                issue.update(fields=fields)

            # Handle transition separately
            if transition is not None:
                available = self.jira.transitions(issue)
                match = None
                for t in available:
                    if t["name"].lower() == transition.lower():
                        match = t
                        break
                if match is None:
                    available_names = [t["name"] for t in available]
                    raise ValueError(
                        f"Transition '{transition}' not found. "
                        f"Available transitions: {available_names}"
                    )
                self.jira.transition_issue(issue, match["id"])

            return {
                "key": ticket_key,
                "status": "updated",
                "url": f"{self.jira_url}/browse/{ticket_key}",
            }
        except JIRAError as e:
            raise Exception(f"Jira API error: {e.text}") from e
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Error updating issue {ticket_key}: {str(e)}") from e

    def add_comment(self, ticket_key: str, body: str) -> dict[str, Any]:
        """
        Add a comment to a Jira issue.

        Returns:
            Dictionary with comment ID, author, and creation timestamp
        """
        try:
            comment = self.jira.add_comment(ticket_key, body)
            return {
                "comment_id": comment.id,
                "author": getattr(comment.author, "displayName", "Unknown"),
                "created": comment.created,
            }
        except JIRAError as e:
            raise Exception(f"Jira API error: {e.text}") from e
        except Exception as e:
            raise Exception(f"Error adding comment to {ticket_key}: {str(e)}") from e

    def get_transitions(self, ticket_key: str) -> list[dict[str, Any]]:
        """
        Get available workflow transitions for a Jira issue.

        Returns:
            List of transition dictionaries with id and name
        """
        try:
            transitions = self.jira.transitions(ticket_key)
            return [{"id": t["id"], "name": t["name"]} for t in transitions]
        except JIRAError as e:
            raise Exception(f"Jira API error: {e.text}") from e
        except Exception as e:
            raise Exception(
                f"Error getting transitions for {ticket_key}: {str(e)}"
            ) from e

    def search_tickets(self, jql: str, max_results: int = 50) -> list[dict[str, Any]]:
        """
        Search for tickets using JQL (Jira Query Language).

        Returns:
            List of ticket data dictionaries
        """
        try:
            issues = self.jira.search_issues(
                jql,
                maxResults=max_results,
                fields="summary,status,issuetype,priority,assignee,labels,resolution,created,updated,description",
            )
            tickets = []

            for issue in issues:
                ticket_data = {
                    "key": issue.key,
                    "summary": issue.fields.summary,
                    "description": getattr(issue.fields, "description", None),
                    "status": self._status_name(issue.fields.status),
                    "issue_type": issue.fields.issuetype.name
                    if issue.fields.issuetype
                    else None,
                    "priority": (
                        getattr(issue.fields.priority, "name", None)
                        if issue.fields.priority
                        else None
                    ),
                    "assignee": (
                        getattr(issue.fields.assignee, "displayName", None)
                        if issue.fields.assignee
                        else None
                    ),
                    "labels": issue.fields.labels if issue.fields.labels else [],
                    "resolution": (
                        getattr(issue.fields.resolution, "name", None)
                        if issue.fields.resolution
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

    def update_ticket(self, ticket_key: str, fields: dict[str, Any]) -> dict[str, Any]:
        """
        Update fields on a Jira ticket.

        Uses the REST API directly to support both standard and Forge-based
        custom fields (e.g. the rh-cf-single-select / rh-cf-multi-select
        fields used for RCA/EDA dropdowns).

        Args:
            ticket_key: Jira ticket key (e.g. ECOENGCL-452)
            fields: Dict mapping field IDs or names to their new values.
                    Accepts both customfield_NNNNN IDs and human-readable
                    field names (resolved via the field map).

        Returns:
            Dictionary with update status and the rendered values of updated
            fields for confirmation.
        """
        try:
            field_map = self._get_field_map()
            name_to_id = {v: k for k, v in field_map.items()}

            resolved: dict[str, Any] = {}
            for key, value in fields.items():
                if key.startswith("customfield_") or not key.startswith("custom"):
                    resolved[key] = value
                else:
                    field_id = name_to_id.get(key, key)
                    resolved[field_id] = field_id if field_id != key else key
                    resolved[field_id] = value

            resp = self.jira._session.put(
                f"{self.jira_url}/rest/api/2/issue/{ticket_key}",
                json={"fields": resolved},
            )

            if resp.status_code == 204:
                confirm_ids = [k for k in resolved if k.startswith("customfield_")]
                rendered_vals: dict[str, str | None] = {}
                if confirm_ids:
                    get_resp = self.jira._session.get(
                        f"{self.jira_url}/rest/api/3/issue/{ticket_key}",
                        params={
                            "fields": ",".join(confirm_ids),
                            "expand": "renderedFields",
                        },
                    )
                    if get_resp.status_code == 200:
                        rdata = get_resp.json().get("renderedFields", {})
                        for fid in confirm_ids:
                            fname = field_map.get(fid, fid)
                            rendered_vals[fname] = rdata.get(fid)

                return {
                    "status": "success",
                    "ticket": ticket_key,
                    "fields_updated": list(resolved.keys()),
                    "rendered_values": rendered_vals,
                    "url": f"{self.jira_url}/browse/{ticket_key}",
                }

            error_text = resp.text if resp.text else f"HTTP {resp.status_code}"
            raise Exception(f"Update failed: {error_text}")

        except JIRAError as e:
            raise Exception(f"Jira API error: {e.text}") from e
        except Exception as e:
            if "Update failed" in str(e) or "Jira API error" in str(e):
                raise
            raise Exception(f"Error updating ticket {ticket_key}: {str(e)}") from e

    def add_comment(self, ticket_key: str, body: str) -> dict[str, Any]:
        """
        Add a comment to a Jira ticket.

        Args:
            ticket_key: Jira ticket key (e.g. ECOENGCL-452)
            body: Comment body in Jira wiki markup format.

        Returns:
            Dictionary with comment ID and metadata.
        """
        try:
            resp = self.jira._session.post(
                f"{self.jira_url}/rest/api/2/issue/{ticket_key}/comment",
                json={"body": body},
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                return {
                    "status": "success",
                    "comment_id": data.get("id"),
                    "ticket": ticket_key,
                    "author": data.get("author", {}).get("displayName"),
                    "created": data.get("created"),
                    "url": f"{self.jira_url}/browse/{ticket_key}"
                    f"?focusedId={data.get('id')}",
                }
            error_text = resp.text if resp.text else f"HTTP {resp.status_code}"
            raise Exception(f"Add comment failed: {error_text}")

        except JIRAError as e:
            raise Exception(f"Jira API error: {e.text}") from e
        except Exception as e:
            if "Add comment failed" in str(e) or "Jira API error" in str(e):
                raise
            raise Exception(f"Error adding comment to {ticket_key}: {str(e)}") from e

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
