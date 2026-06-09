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
        self.jira_url = os.environ.get("JIRA_URL", "https://redhat.atlassian.net")
        self.jira_token = os.environ.get("JIRA_API_TOKEN")
        self.jira_email = os.environ.get("JIRA_EMAIL")

        if not self.jira_token:
            raise ValueError(
                "JIRA_API_TOKEN environment variable must be set. "
                "See documentation for setup instructions."
            )

        if self.jira_email:
            self.jira = JIRA(
                server=self.jira_url,
                basic_auth=(self.jira_email, self.jira_token),
            )
        else:
            self.jira = JIRA(server=self.jira_url, token_auth=self.jira_token)
        self._field_map: dict[str, str] | None = None
        self._user_field_ids: set[str] | None = None
        self._multi_user_field_ids: set[str] | None = None
        self._status_name_map: dict[str, str] | None = None
        self._is_cloud = "atlassian.net" in self.jira_url

    def _resolve_assignee(self, assignee: str) -> dict[str, str] | None:
        """Resolve an assignee string to the correct Jira field format.

        Jira Cloud requires {"accountId": "..."} while Jira Server/DC
        uses {"name": "..."}.  Pass an empty string or "none" to unassign.
        """
        if assignee.strip().lower() in ("", "none", "unassigned"):
            return None

        if not self._is_cloud:
            return {"name": assignee}

        users = self.jira._session.get(
            f"{self.jira_url}/rest/api/2/user/search",
            params={"query": assignee, "maxResults": 1},
        ).json()
        if users:
            return {"accountId": users[0]["accountId"]}

        raise ValueError(
            f"Could not find Jira Cloud user matching '{assignee}'. "
            "Provide an email address or display name."
        )

    def get_forge_field_options(
        self,
        ticket_key: str,
        field_id: str,
    ) -> dict[str, Any]:
        """Get known values for a Forge custom field.

        Searches existing tickets in the same project for unique
        rendered values of the field. This discovers all options that
        have been used at least once.

        Args:
            ticket_key: Issue key (e.g. PROJ-123) — the project
                is derived from this key.
            field_id: Custom field ID (e.g. customfield_12345).

        Returns:
            Dict with ``field_name``, ``options`` list and
            ``total_tickets_sampled``.
        """
        field_map = self._get_field_map()
        field_name = field_map.get(field_id, field_id)
        project_key = ticket_key.split("-")[0]

        # Determine if multi-select from editmeta schema type
        multi_select = False
        try:
            meta_resp = self.jira._session.get(
                f"{self.jira_url}/rest/api/2/issue/{ticket_key}/editmeta"
            )
            if meta_resp.status_code == 200:
                meta = meta_resp.json().get("fields", {}).get(field_id, {})
                multi_select = meta.get("schema", {}).get("type") == "array"
        except Exception:
            pass

        # Collect known values from existing tickets via search
        cf_num = field_id.replace("customfield_", "")
        jql = (
            f"project = {project_key} "
            f"AND cf[{cf_num}] is not EMPTY "
            f"ORDER BY updated DESC"
        )
        resp = self.jira._session.get(
            f"{self.jira_url}/rest/api/3/search/jql",
            params={
                "jql": jql,
                "maxResults": 100,
                "fields": field_id,
                "expand": "renderedFields",
            },
        )
        if resp.status_code != 200:
            raise Exception(
                f"Search failed (HTTP {resp.status_code}): {resp.text[:300]}"
            )
        data = resp.json()
        values: set[str] = set()
        for iss in data.get("issues", []):
            rendered = iss.get("renderedFields", {}).get(field_id)
            if not rendered or not isinstance(rendered, str):
                continue
            raw = iss.get("fields", {}).get(field_id)
            if isinstance(raw, list):
                for part in rendered.split(", "):
                    stripped = part.strip()
                    if stripped:
                        values.add(stripped)
            else:
                values.add(rendered)

        return {
            "field_id": field_id,
            "field_name": field_name,
            "multi_select": multi_select,
            "options": sorted(values),
            "total_tickets_sampled": data.get("total", 0),
        }

    def _fetch_rendered_fields(self, ticket_key: str) -> dict[str, Any] | None:
        """Fetch renderedFields for an issue.

        Forge/Connect app custom fields return encrypted values through
        the standard API. The renderedFields expansion asks Jira to
        server-side render values through the app, returning readable text.
        """
        try:
            resp = self.jira._session.get(
                f"{self.jira_url}/rest/api/2/issue/{ticket_key}",
                params={"fields": "*all", "expand": "renderedFields"},
            )
            return resp.json().get("renderedFields", {})
        except Exception:
            return None

    def _get_field_map(self) -> dict[str, str]:
        """Get field ID to name mapping, cached per instance.

        Also populates ``_user_field_ids`` and ``_multi_user_field_ids``
        so that ``update_issue`` can resolve user-type custom fields.
        """
        if self._field_map is None:
            try:
                fields = self.jira.fields()
                self._field_map = {}
                user_ids: set[str] = set()
                multi_user_ids: set[str] = set()
                for f in fields:
                    self._field_map[f["id"]] = f["name"]
                    schema = f.get("schema", {})
                    custom = schema.get("custom", "")
                    if schema.get("type") == "user" or custom.endswith(":userpicker"):
                        user_ids.add(f["id"])
                    elif custom.endswith(":multiuserpicker"):
                        multi_user_ids.add(f["id"])
                self._user_field_ids = user_ids
                self._multi_user_field_ids = multi_user_ids
            except Exception:
                self._field_map = {}
                self._user_field_ids = set()
                self._multi_user_field_ids = set()
        return self._field_map

    def get_ticket_data(
        self,
        ticket_key: str,
        max_comments: int = 10,
        comment_offset: int = 0,
    ) -> dict[str, Any]:
        """
        Get comprehensive ticket data including comments.

        Args:
            ticket_key: Jira ticket key (e.g. PROJ-123)
            max_comments: Maximum number of comments to return
            comment_offset: Number of comments to skip for pagination

        Returns:
            Dictionary containing ticket data and comments
        """
        try:
            # Get the issue
            issue = self.jira.issue(ticket_key, expand="changelog")

            # Extract basic ticket information
            comment_obj = getattr(issue.fields, "comment", None)
            total_comments = (
                len(comment_obj.comments) if comment_obj and comment_obj.comments else 0
            )

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
                "parent": self._get_parent(issue),
                "total_comments": total_comments,
                "url": f"{self.jira_url}/browse/{issue.key}",
            }

            # Extract custom fields and additional standard fields
            # not already in ticket_data.
            # Forge/Connect app fields return encrypted values in the
            # standard response; renderedFields decrypts them.
            field_map = self._get_field_map()
            raw_fields = issue.raw.get("fields", {})
            rendered_fields = self._fetch_rendered_fields(ticket_key) or {}
            already_extracted = {
                "summary",
                "description",
                "status",
                "priority",
                "issuetype",
                "assignee",
                "reporter",
                "created",
                "updated",
                "resolution",
                "labels",
                "components",
                "fixVersions",
                "versions",
                "comment",
                "parent",
                "issuelinks",
            }
            custom_fields = {}
            custom_field_ids = {}
            for field_id, raw_value in raw_fields.items():
                if field_id in already_extracted:
                    continue
                if raw_value is None:
                    continue
                rendered = rendered_fields.get(field_id)
                if rendered is not None and field_id.startswith("customfield_"):
                    if isinstance(raw_value, str) and raw_value != rendered:
                        raw_value = rendered
                    elif isinstance(raw_value, list) and isinstance(rendered, str):
                        raw_value = rendered
                field_name = field_map.get(field_id, field_id)
                custom_fields[field_name] = _simplify_field_value(raw_value)
                if field_id.startswith("customfield_"):
                    custom_field_ids[field_name] = field_id
            if custom_fields:
                ticket_data["custom_fields"] = custom_fields
            if custom_field_ids:
                ticket_data["custom_field_ids"] = custom_field_ids

            # Get web links (remote links)
            ticket_data["web_links"] = self._get_web_links(ticket_key)

            # Get issue links (linked Jira tickets)
            ticket_data["issue_links"] = self._get_issue_links(issue)

            # Get comments
            comments = self._get_comments(issue, max_comments, comment_offset)
            ticket_data["comments"] = comments

            # Get changelog/history
            changelog = self._get_changelog(issue)
            ticket_data["changelog"] = changelog

            # Get remote links (web links)
            remote_links = self._get_remote_links(ticket_key)
            if remote_links:
                ticket_data["remote_links"] = remote_links

            return ticket_data

        except JIRAError as e:
            raise Exception(f"Jira API error: {e.text}") from e
        except Exception as e:
            raise Exception(f"Error retrieving ticket {ticket_key}: {str(e)}") from e

    def _get_comments(
        self, issue: Any, max_comments: int, offset: int = 0
    ) -> list[dict[str, Any]]:
        """Extract comments from the issue with pagination support."""
        comments = []

        if hasattr(issue.fields, "comment") and issue.fields.comment:
            comment_list = issue.fields.comment.comments
            page = comment_list[offset : offset + max_comments]

            for comment in page:
                comment_data = {
                    "id": comment.id,
                    "author": getattr(comment.author, "displayName", "Unknown"),
                    "body": comment.body,
                    "created": comment.created,
                    "updated": comment.updated,
                }
                comments.append(comment_data)

        return comments

    def _get_remote_links(self, ticket_key: str) -> list[dict[str, Any]]:
        """Fetch remote links (web links) for an issue."""
        try:
            links = self.jira.remote_links(ticket_key)
            result = []
            for link in links:
                link_obj = getattr(link, "object", None) or {}
                if isinstance(link_obj, dict):
                    url = link_obj.get("url")
                    title = link_obj.get("title")
                else:
                    url = getattr(link_obj, "url", None)
                    title = getattr(link_obj, "title", None)
                result.append(
                    {
                        "id": getattr(link, "id", None),
                        "url": url,
                        "title": title,
                    }
                )
            return result
        except Exception:
            return []

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

    def _get_parent(self, issue: Any) -> dict[str, str | None] | None:
        """Extract parent ticket info (Epic, Story, etc.)."""
        parent = getattr(issue.fields, "parent", None)
        if parent is None:
            return None
        return {
            "key": parent.key,
            "summary": getattr(parent.fields, "summary", None),
            "issue_type": (
                getattr(parent.fields.issuetype, "name", None)
                if getattr(parent.fields, "issuetype", None)
                else None
            ),
        }

    def _get_web_links(self, ticket_key: str) -> list[dict[str, str]]:
        """Fetch remote (web) links for an issue."""
        try:
            remote_links = self.jira.remote_links(ticket_key)
            return [
                {
                    "url": link.object.url,
                    "title": getattr(link.object, "title", link.object.url),
                }
                for link in remote_links
                if hasattr(link, "object") and hasattr(link.object, "url")
            ]
        except Exception:
            return []

    def _get_issue_links(self, issue: Any) -> list[dict[str, str | None]]:
        """Extract issue links (linked Jira tickets) from an issue."""
        links: list[dict[str, str | None]] = []
        issue_links = getattr(issue.fields, "issuelinks", None)
        if not issue_links:
            return links
        for link in issue_links:
            link_type = getattr(link.type, "name", "Related")
            if hasattr(link, "outwardIssue"):
                target = link.outwardIssue
                direction = getattr(link.type, "outward", link_type)
            elif hasattr(link, "inwardIssue"):
                target = link.inwardIssue
                direction = getattr(link.type, "inward", link_type)
            else:
                continue
            links.append(
                {
                    "key": target.key,
                    "summary": getattr(target.fields, "summary", None),
                    "direction": direction,
                    "link_type": link_type,
                }
            )
        return links

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
                fields["assignee"] = self._resolve_assignee(assignee)

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
        custom_fields: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Update an existing Jira issue.

        Args:
            custom_fields: Dict mapping customfield_NNNNN IDs (or human-readable
                names) to values. Supports Forge/Connect app fields.

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
                fields["assignee"] = self._resolve_assignee(assignee)

            # Resolve human-readable custom field names to IDs
            if custom_fields:
                field_map = self._get_field_map()
                name_to_id = {v: k for k, v in field_map.items()}
                user_ids = self._user_field_ids or set()
                multi_user_ids = self._multi_user_field_ids or set()
                for key, value in custom_fields.items():
                    field_id = name_to_id.get(key, key)
                    if field_id in user_ids and isinstance(value, str):
                        value = self._resolve_assignee(value)
                    elif field_id in multi_user_ids and isinstance(value, str):
                        names = [n.strip() for n in value.split(",") if n.strip()]
                        value = [
                            resolved
                            for n in names
                            if (resolved := self._resolve_assignee(n)) is not None
                        ]
                    fields[field_id] = value

            if fields:
                resp = self.jira._session.put(
                    f"{self.jira_url}/rest/api/2/issue/{ticket_key}",
                    json={"fields": fields},
                )
                if resp.status_code not in (200, 204):
                    error_text = resp.text or f"HTTP {resp.status_code}"
                    raise Exception(f"Update failed: {error_text}")

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

            result: dict[str, Any] = {
                "key": ticket_key,
                "status": "updated",
                "url": f"{self.jira_url}/browse/{ticket_key}",
            }

            # Read back rendered values for custom fields
            cf_ids = [k for k in fields if k.startswith("customfield_")]
            if cf_ids:
                rendered = self._fetch_rendered_fields(ticket_key) or {}
                field_map = self._get_field_map()
                rendered_vals = {}
                for fid in cf_ids:
                    fname = field_map.get(fid, fid)
                    rendered_vals[fname] = rendered.get(fid)
                result["rendered_values"] = rendered_vals

            return result
        except JIRAError as e:
            raise Exception(f"Jira API error: {e.text}") from e
        except ValueError:
            raise
        except Exception as e:
            if "Update failed" in str(e):
                raise
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

    def add_weblink(self, ticket_key: str, url: str, title: str) -> dict[str, Any]:
        """Add a web link (remote link) to a Jira issue.

        Returns:
            Dictionary with link ID and URL
        """
        try:
            link = self.jira.add_simple_link(ticket_key, {"url": url, "title": title})
            return {
                "link_id": link.id if hasattr(link, "id") else str(link),
                "url": url,
                "title": title,
            }
        except JIRAError as e:
            raise Exception(f"Jira API error: {e.text}") from e
        except Exception as e:
            raise Exception(f"Error adding web link to {ticket_key}: {str(e)}") from e

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

    def search_tickets(
        self, jql: str, max_results: int = 50, offset: int = 0
    ) -> dict[str, Any]:
        """
        Search for tickets using JQL (Jira Query Language).

        Args:
            jql: JQL query string
            max_results: Maximum number of results to return
            offset: Number of results to skip for pagination

        Returns:
            Dictionary with total_count and items list
        """
        try:
            issues = self.jira.search_issues(
                jql,
                startAt=offset,
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

            return {
                "total_count": issues.total,
                "offset": offset,
                "limit": max_results,
                "items": tickets,
            }

        except JIRAError as e:
            raise Exception(f"Jira search error: {e.text}") from e
        except Exception as e:
            raise Exception(f"Error searching tickets: {str(e)}") from e

    def count_tickets(self, jql: str) -> int:
        """Count tickets matching a JQL query.

        On Jira Cloud uses the approximate-count endpoint.
        On Jira Server/DC uses a minimal search with maxResults=0.
        """
        if self._is_cloud:
            resp = self.jira._session.post(
                f"{self.jira_url}/rest/api/3/search/approximate-count",
                json={"jql": jql},
            )
            resp.raise_for_status()
            return resp.json().get("count", 0)

        issues = self.jira.search_issues(jql, maxResults=0)
        return issues.total

    def _search_all(self, jql: str, fields: str) -> list[Any]:
        """Search Jira and auto-paginate to collect all results."""
        all_issues: list[Any] = []
        start = 0
        batch = 100
        while True:
            issues = self.jira.search_issues(
                jql, startAt=start, maxResults=batch, fields=fields
            )
            all_issues.extend(issues)
            if start + batch >= issues.total:
                break
            start += batch
        return all_issues

    def search_child_tickets(
        self,
        parent_jql: str,
        child_jql: str,
        parent_link_field: str = "parent",
        child_link_field: str = "parentEpic",
        max_results: int = 200,
    ) -> dict[str, Any]:
        """Traverse a 2-level Jira hierarchy and return leaf tickets with ancestry.

        Level 0 (grandparents): found via parent_jql
        Level 1 (intermediates): found via ``{parent_link_field} = <grandparent>``
        Level 2 (leaves): found via ``{child_link_field} = <intermediate> AND {child_jql}``

        Returns:
            Dict with grandparent_tickets, intermediate_tickets, tickets, and counts.
        """
        try:
            # Level 0: grandparents
            gp_issues = self._search_all(parent_jql, "summary,status,labels")
            grandparent_tickets = []
            gp_keys = []
            for issue in gp_issues:
                gp_data = {
                    "key": issue.key,
                    "summary": issue.fields.summary,
                    "status": self._status_name(issue.fields.status),
                    "labels": issue.fields.labels if issue.fields.labels else [],
                }
                grandparent_tickets.append(gp_data)
                gp_keys.append(issue.key)

            if not gp_keys:
                return {
                    "grandparent_tickets": [],
                    "intermediate_tickets": [],
                    "tickets": [],
                    "total_grandparents": 0,
                    "total_intermediates": 0,
                    "total_tickets": 0,
                }

            # Level 1: intermediates (e.g. epics) — one search per grandparent
            intermediate_tickets = []
            int_keys = []
            int_to_gp: dict[str, str] = {}
            for gp_key in gp_keys:
                jql = f"{parent_link_field} = {gp_key}"
                issues = self._search_all(jql, "summary,status")
                for issue in issues:
                    int_data = {
                        "key": issue.key,
                        "summary": issue.fields.summary,
                        "status": self._status_name(issue.fields.status),
                        "grandparent_key": gp_key,
                    }
                    intermediate_tickets.append(int_data)
                    int_keys.append(issue.key)
                    int_to_gp[issue.key] = gp_key

            if not int_keys:
                return {
                    "grandparent_tickets": grandparent_tickets,
                    "intermediate_tickets": [],
                    "tickets": [],
                    "total_grandparents": len(grandparent_tickets),
                    "total_intermediates": 0,
                    "total_tickets": 0,
                }

            # Build grandparent lookup for enrichment
            gp_lookup = {gp["key"]: gp for gp in grandparent_tickets}

            # Level 2: leaves — one search per intermediate
            tickets = []
            for int_key in int_keys:
                jql = f"{child_link_field} = {int_key}"
                if child_jql:
                    jql += f" AND {child_jql}"
                issues = self._search_all(
                    jql, "summary,status,assignee,created,updated"
                )
                gp_key = int_to_gp[int_key]
                gp_data = gp_lookup.get(gp_key, {})
                for issue in issues:
                    ticket = {
                        "key": issue.key,
                        "summary": issue.fields.summary,
                        "status": self._status_name(issue.fields.status),
                        "assignee": (
                            getattr(issue.fields.assignee, "displayName", None)
                            if issue.fields.assignee
                            else None
                        ),
                        "created": issue.fields.created,
                        "updated": issue.fields.updated,
                        "url": f"{self.jira_url}/browse/{issue.key}",
                        "parent_key": int_key,
                        "grandparent_key": gp_key,
                        "grandparent_summary": gp_data.get("summary"),
                        "grandparent_status": gp_data.get("status"),
                        "grandparent_labels": gp_data.get("labels", []),
                    }
                    tickets.append(ticket)
                    if len(tickets) >= max_results:
                        break
                if len(tickets) >= max_results:
                    break

            return {
                "grandparent_tickets": grandparent_tickets,
                "intermediate_tickets": intermediate_tickets,
                "tickets": tickets,
                "total_grandparents": len(grandparent_tickets),
                "total_intermediates": len(intermediate_tickets),
                "total_tickets": len(tickets),
            }

        except JIRAError as e:
            raise Exception(f"Jira search error: {e.text}") from e
        except Exception as e:
            raise Exception(f"Error in child ticket search: {str(e)}") from e

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

    def get_filter(self, filter_id: str) -> dict[str, Any]:
        """Get a saved filter's definition by ID.

        Returns:
            Dictionary with filter id, name, jql, description, and owner.
        """
        try:
            f = self.jira.filter(filter_id)
            return {
                "id": f.id,
                "name": f.name,
                "jql": getattr(f, "jql", None),
                "description": getattr(f, "description", None),
                "owner": getattr(getattr(f, "owner", None), "displayName", None),
                "favourite": getattr(f, "favourite", None),
                "url": getattr(f, "viewUrl", None),
            }
        except JIRAError as e:
            raise Exception(f"Jira API error: {e.text}") from e
        except Exception as e:
            raise Exception(f"Error retrieving filter {filter_id}: {str(e)}") from e

    def get_favourite_filters(self) -> list[dict[str, Any]]:
        """Get the authenticated user's favourite filters.

        Returns:
            List of filter dictionaries with id, name, jql, description.
        """
        try:
            filters = self.jira.favourite_filters()
            return [
                {
                    "id": f.id,
                    "name": f.name,
                    "jql": getattr(f, "jql", None),
                    "description": getattr(f, "description", None),
                    "owner": getattr(getattr(f, "owner", None), "displayName", None),
                    "url": getattr(f, "viewUrl", None),
                }
                for f in filters
            ]
        except JIRAError as e:
            raise Exception(f"Jira API error: {e.text}") from e
        except Exception as e:
            raise Exception(f"Error retrieving favourite filters: {str(e)}") from e

    def search_filters(self, filter_name: str) -> list[dict[str, Any]]:
        """Search for Jira filters by name.

        Uses the REST API filter/search endpoint with filterName parameter.

        Returns:
            List of matching filter dictionaries.
        """
        try:
            resp = self.jira._session.get(
                f"{self.jira_url}/rest/api/3/filter/search",
                params={"filterName": filter_name, "expand": "jql,description"},
            )
            data = resp.json()
            return [
                {
                    "id": f["id"],
                    "name": f.get("name"),
                    "jql": f.get("jql"),
                    "description": f.get("description"),
                    "owner": (f.get("owner") or {}).get("displayName"),
                    "favourite": f.get("favourite"),
                    "url": f.get("viewUrl"),
                }
                for f in data.get("values", [])
            ]
        except JIRAError as e:
            raise Exception(f"Jira API error: {e.text}") from e
        except Exception as e:
            raise Exception(
                f"Error searching filters by name '{filter_name}': {str(e)}"
            ) from e

    def get_project_components(self, project_key: str) -> list[dict[str, Any]]:
        """Get components for a project.

        Returns:
            List of component dictionaries with id, name, description, lead.
        """
        try:
            components = self.jira.project_components(project_key)
            return [
                {
                    "id": c.id,
                    "name": c.name,
                    "description": getattr(c, "description", None),
                    "lead": getattr(getattr(c, "lead", None), "displayName", None),
                    "assignee_type": getattr(c, "assigneeType", None),
                }
                for c in components
            ]
        except JIRAError as e:
            raise Exception(f"Jira API error: {e.text}") from e
        except Exception as e:
            raise Exception(
                f"Error retrieving components for {project_key}: {str(e)}"
            ) from e

    def get_project_versions(self, project_key: str) -> list[dict[str, Any]]:
        """Get versions for a project.

        Returns:
            List of version dictionaries with id, name, released, archived, dates.
        """
        try:
            versions = self.jira.project_versions(project_key)
            return [
                {
                    "id": v.id,
                    "name": v.name,
                    "description": getattr(v, "description", None),
                    "released": getattr(v, "released", None),
                    "archived": getattr(v, "archived", None),
                    "release_date": getattr(v, "releaseDate", None),
                    "start_date": getattr(v, "startDate", None),
                }
                for v in versions
            ]
        except JIRAError as e:
            raise Exception(f"Jira API error: {e.text}") from e
        except Exception as e:
            raise Exception(
                f"Error retrieving versions for {project_key}: {str(e)}"
            ) from e

    def get_issue_types_for_project(self, project_key: str) -> list[dict[str, Any]]:
        """Get available issue types for a project.

        Returns:
            List of issue type dictionaries with id, name, subtask, description.
        """
        try:
            issue_types = self.jira.issue_types_for_project(project_key)
            return [
                {
                    "id": it.id,
                    "name": it.name,
                    "subtask": getattr(it, "subtask", False),
                    "description": getattr(it, "description", None),
                }
                for it in issue_types
            ]
        except JIRAError as e:
            raise Exception(f"Jira API error: {e.text}") from e
        except Exception as e:
            raise Exception(
                f"Error retrieving issue types for {project_key}: {str(e)}"
            ) from e

    def get_boards(
        self,
        project_key: str | None = None,
        board_type: str | None = None,
        name: str | None = None,
        max_results: int = 50,
        start_at: int = 0,
    ) -> dict[str, Any]:
        """Get boards, optionally filtered by project, type, or name.

        Returns:
            Dictionary with total and items list of board dictionaries.
        """
        try:
            boards = self.jira.boards(
                startAt=start_at,
                maxResults=max_results,
                type=board_type,
                name=name,
                projectKeyOrID=project_key,
            )
            return {
                "total": getattr(boards, "total", len(boards)),
                "start_at": start_at,
                "max_results": max_results,
                "items": [
                    {
                        "id": b.id,
                        "name": b.name,
                        "type": getattr(b, "type", None),
                    }
                    for b in boards
                ],
            }
        except JIRAError as e:
            raise Exception(f"Jira API error: {e.text}") from e
        except Exception as e:
            raise Exception(f"Error retrieving boards: {str(e)}") from e

    def get_sprints(
        self,
        board_id: int,
        state: str | None = None,
        max_results: int = 50,
        start_at: int = 0,
    ) -> dict[str, Any]:
        """Get sprints for a board.

        Returns:
            Dictionary with total and items list of sprint dictionaries.
        """
        try:
            sprints = self.jira.sprints(
                board_id=board_id,
                startAt=start_at,
                maxResults=max_results,
                state=state,
            )
            return {
                "total": getattr(sprints, "total", len(sprints)),
                "start_at": start_at,
                "max_results": max_results,
                "items": [
                    {
                        "id": s.id,
                        "name": s.name,
                        "state": getattr(s, "state", None),
                        "start_date": getattr(s, "startDate", None),
                        "end_date": getattr(s, "endDate", None),
                        "complete_date": getattr(s, "completeDate", None),
                        "goal": getattr(s, "goal", None),
                    }
                    for s in sprints
                ],
            }
        except JIRAError as e:
            raise Exception(f"Jira API error: {e.text}") from e
        except Exception as e:
            raise Exception(
                f"Error retrieving sprints for board {board_id}: {str(e)}"
            ) from e
