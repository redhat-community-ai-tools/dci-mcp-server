"""MCP tools for Jira ticket operations."""

import json
import re
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ..services.jira_service import JiraService


def validate_ticket_key(ticket_key: str) -> str:
    """
    Validate and normalize Jira ticket key format.

    Args:
        ticket_key: Ticket key in format PROJECT-NUMBER (e.g., CILAB-1234)

    Returns:
        Normalized ticket key

    Raises:
        ValueError: If ticket key format is invalid
    """
    # Remove any whitespace
    ticket_key = ticket_key.strip()

    # Pattern to match PROJECT-NUMBER format
    pattern = r"^[A-Z][A-Z0-9]+-\d+$"

    if not re.match(pattern, ticket_key):
        raise ValueError(
            f"Invalid ticket key format: '{ticket_key}'. "
            "Expected format: PROJECT-NUMBER (e.g., CILAB-1234, OCP-5678)"
        )

    return ticket_key.upper()


def register_jira_tools(mcp: FastMCP) -> None:
    """Register Jira-related tools with the MCP server."""

    @mcp.tool()
    async def get_jira_ticket(
        ticket_key: Annotated[
            str,
            Field(
                description="Jira ticket key in format PROJECT-NUMBER (e.g., CILAB-1234, OCP-5678)"
            ),
        ],
        max_comments: Annotated[
            int,
            Field(
                description="Maximum number of comments to retrieve (default: 10, max: 50)",
                ge=1,
                le=50,
            ),
        ] = 10,
        comment_offset: Annotated[
            int,
            Field(
                description="Number of comments to skip for pagination (default: 0)",
                ge=0,
            ),
        ] = 0,
    ) -> str:
        """Get comprehensive Jira ticket data including comments and changelog.

        This tool retrieves detailed information about a Jira ticket including:
        - Basic ticket information (summary, description, status, priority, etc.)
        - Date information (created, updated)
        - Assignee and reporter information
        - Labels, components, and versions
        - Recent comments (up to the specified limit)
        - Changelog/history of changes

        ## Authentication Required

        This tool requires Jira API authentication. Set the following environment variables:
        - `JIRA_API_TOKEN`: Your Jira API token
        - `JIRA_URL`: Jira server URL (defaults to https://redhat.atlassian.net)

        ## Getting Your Jira API Token

        1. Go to https://redhat.atlassian.net/secure/ViewProfile.jspa
        2. Click on "Personal Access Tokens" in the left sidebar
        3. Click "Create token"
        4. Give your token a name (e.g., "DCI MCP Server")
        5. Set an expiration date (optional but recommended)
        6. Click "Create"
        7. Copy the generated token and set it as `JIRA_API_TOKEN` in your environment

        ## Ticket Key Format

        The ticket key should be in the format `PROJECT-NUMBER`:
        - Examples: `CILAB-1234`, `OCP-5678`, `RHEL-9999`
        - Case insensitive (will be converted to uppercase)
        - Must match the pattern: [A-Z][A-Z0-9]+-[0-9]+

        ## Returned Data

        The tool returns a JSON object containing:
        - **Basic Info**: key, summary, description, status, priority, issue_type
        - **People**: assignee, reporter
        - **Dates**: created, updated
        - **Classification**: labels, components, fix_versions, affected_versions
        - **Custom Fields**: custom_fields dict with human-readable field names as keys
          (only non-null custom fields are included)
        - **Custom Field IDs**: custom_field_ids dict mapping field names to their
          customfield_NNNNN IDs (use these IDs or names with update_jira_ticket's
          custom_fields parameter to update values)
        - **total_comments**: Total number of comments on the ticket
        - **Comments**: Comments with author, body, timestamps (paginated)
        - **Changelog**: History of changes with field modifications
        - **URL**: Direct link to the ticket

        Use comment_offset and max_comments to paginate through comments.

        Returns:
            JSON string with comprehensive ticket data
        """
        try:
            # Validate and normalize ticket key
            normalized_key = validate_ticket_key(ticket_key)

            # Initialize Jira service
            jira_service = JiraService()

            # Get ticket data
            ticket_data = jira_service.get_ticket_data(
                normalized_key, max_comments, comment_offset
            )

            return json.dumps(ticket_data, indent=2)

        except ValueError as e:
            return json.dumps({"error": str(e)}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def search_jira_tickets(
        jql: Annotated[
            str,
            Field(
                description="JQL (Jira Query Language) query string. Examples: 'project = CILAB AND status = Open', 'assignee = currentUser() AND status != Closed'"
            ),
        ],
        max_results: Annotated[
            int,
            Field(
                description="Maximum number of results to return (default: 50, max: 200)",
                ge=1,
                le=200,
            ),
        ] = 50,
        offset: Annotated[
            int,
            Field(
                description="Number of results to skip for pagination (default: 0)",
                ge=0,
            ),
        ] = 0,
    ) -> str:
        """Search Jira tickets using JQL (Jira Query Language).

        This tool allows you to search for tickets using JQL queries, which is Jira's
        powerful query language for finding issues.

        ## Authentication Required

        This tool requires Jira API authentication. Set the following environment variables:
        - `JIRA_API_TOKEN`: Your Jira API token
        - `JIRA_URL`: Jira server URL (defaults to https://redhat.atlassian.net)

        ## JQL Examples

        **Basic Queries:**
        - `project = CILAB` - All tickets in CILAB project
        - `status = Open` - All open tickets
        - `assignee = currentUser()` - Tickets assigned to you
        - `reporter = currentUser()` - Tickets reported by you

        **Advanced Queries:**
        - `project = CILAB AND status in (Open, "In Progress")` - Open or in-progress CILAB tickets
        - `assignee = currentUser() AND status != Closed` - Your non-closed tickets
        - `created >= -7d` - Tickets created in the last 7 days
        - `updated >= -1d` - Tickets updated in the last day
        - `text ~ "openshift"` - Tickets containing "openshift" in text fields
        - `labels in (bug, critical)` - Tickets with specific labels

        **Date Queries:**
        - `created >= "2024-01-01"` - Tickets created after specific date
        - `updated >= -30d` - Tickets updated in the last 30 days
        - `due <= +7d` - Tickets due within 7 days

        **Component and Version:**
        - `component = "OpenShift"` - Tickets in OpenShift component
        - `fixVersion = "4.19.0"` - Tickets fixed in specific version
        - `affectedVersion = "4.18.0"` - Tickets affecting specific version

        ## Returned Data

        The tool returns a JSON object containing:
        - **total_count**: Total number of matching results
        - **offset**: Number of results skipped
        - **limit**: Maximum results requested
        - **items**: Array of ticket summaries, each with:
          - **key**: Ticket key (e.g., CILAB-1234)
          - **summary**: Ticket title/summary
          - **status**: Current status
          - **assignee**: Assigned user
          - **created**: Creation date
          - **updated**: Last update date
          - **url**: Direct link to the ticket

        Use offset and max_results to paginate through large result sets.

        Returns:
            JSON string with total_count and items array
        """
        try:
            # Initialize Jira service
            jira_service = JiraService()

            # Search tickets
            results = jira_service.search_tickets(jql, max_results, offset)

            return json.dumps(results, indent=2)

        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def get_jira_project_info(
        project_key: Annotated[
            str,
            Field(description="Jira project key (e.g., CILAB, OCP, RHEL)"),
        ],
    ) -> str:
        """Get Jira project information.

        This tool retrieves basic information about a Jira project including
        project name, description, lead, and other metadata.

        ## Authentication Required

        This tool requires Jira API authentication. Set the following environment variables:
        - `JIRA_API_TOKEN`: Your Jira API token
        - `JIRA_URL`: Jira server URL (defaults to https://redhat.atlassian.net)

        ## Project Key Format

        The project key should be the short project identifier:
        - Examples: `CILAB`, `OCP`, `RHEL`, `OPENSHIFT`
        - Case insensitive (will be converted to uppercase)
        - Must be a valid project key in your Jira instance

        ## Returned Data

        The tool returns a JSON object containing:
        - **key**: Project key
        - **name**: Full project name
        - **description**: Project description
        - **lead**: Project lead/owner
        - **url**: Direct link to the project

        Returns:
            JSON string with project information
        """
        try:
            # Normalize project key
            project_key = project_key.strip().upper()

            # Initialize Jira service
            jira_service = JiraService()

            # Get project info
            project_info = jira_service.get_project_info(project_key)

            return json.dumps(project_info, indent=2)

        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def search_jira_child_tickets(
        parent_jql: Annotated[
            str,
            Field(
                description="JQL to find top-level (grandparent) tickets. "
                'Example: "project = TELCOSTRAT AND fixVersion = openshift-4.20"'
            ),
        ],
        child_jql: Annotated[
            str,
            Field(
                description="JQL filter applied to leaf-level tickets. "
                'Example: "project = CNF AND (summary ~ Automation OR summary ~ Regression)"'
            ),
        ],
        parent_link_field: Annotated[
            str,
            Field(
                description='Jira field linking intermediate tickets to grandparents (default: "parent")'
            ),
        ] = "parent",
        child_link_field: Annotated[
            str,
            Field(
                description='Jira field linking leaf tickets to intermediates (default: "parentEpic")'
            ),
        ] = "parentEpic",
        max_results: Annotated[
            int,
            Field(
                description="Maximum leaf tickets to return (default: 200, max: 500)",
                ge=1,
                le=500,
            ),
        ] = 200,
    ) -> str:
        """Traverse a 2-level Jira hierarchy and return leaf tickets with ancestry.

        Performs a top-down search through three levels of Jira tickets:
        1. **Grandparents** (level 0): Found via `parent_jql`
        2. **Intermediates** (level 1): Found via `{parent_link_field} = <grandparent key>`
        3. **Leaves** (level 2): Found via `{child_link_field} = <intermediate key> AND {child_jql}`

        Each leaf ticket includes its full ancestry (parent and grandparent keys,
        summary, status, labels).

        ## Use Case

        Useful for tracing requirements down to test/automation tickets through
        an Epic hierarchy. For example: TELCOSTRAT requirements -> CNF Epics -> CNF Stories.

        ## Authentication Required

        Requires `JIRA_API_TOKEN` environment variable.

        ## Returned Data

        Returns a JSON object with:
        - **grandparent_tickets**: List of top-level tickets (key, summary, status, labels)
        - **intermediate_tickets**: List of mid-level tickets (key, summary, status, grandparent_key)
        - **tickets**: List of leaf tickets with full ancestry info
        - **total_grandparents**, **total_intermediates**, **total_tickets**: Counts

        Returns:
            JSON string with hierarchical ticket data
        """
        try:
            jira_service = JiraService()
            results = jira_service.search_child_tickets(
                parent_jql=parent_jql,
                child_jql=child_jql,
                parent_link_field=parent_link_field,
                child_link_field=child_link_field,
                max_results=max_results,
            )
            return json.dumps(results, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
