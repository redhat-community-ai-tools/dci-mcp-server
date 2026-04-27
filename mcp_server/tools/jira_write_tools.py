"""MCP tools for Jira write operations (create/update tickets, add comments)."""

import json
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ..services.jira_service import JiraService
from .jira_tools import validate_ticket_key


def register_jira_write_tools(mcp: FastMCP) -> None:
    """Register Jira write tools with the MCP server."""

    @mcp.tool()
    async def create_jira_ticket(
        project_key: Annotated[
            str,
            Field(description="Jira project key (e.g., CILAB, OCP, RHEL)"),
        ],
        summary: Annotated[
            str,
            Field(description="Ticket summary/title"),
        ],
        description: Annotated[
            str | None,
            Field(description="Ticket description (supports Jira wiki markup)"),
        ] = None,
        issue_type: Annotated[
            str,
            Field(
                description="Issue type (e.g., Task, Bug, Story, Epic). Default: Task"
            ),
        ] = "Task",
        priority: Annotated[
            str | None,
            Field(
                description="Priority name (e.g., Blocker, Critical, Major, Minor, Trivial)"
            ),
        ] = None,
        labels: Annotated[
            list[str] | None,
            Field(description="List of labels to set on the ticket"),
        ] = None,
        components: Annotated[
            list[str] | None,
            Field(description="List of component names to set on the ticket"),
        ] = None,
        assignee: Annotated[
            str | None,
            Field(
                description="Assignee username (Jira Server/DC) or account ID (Jira Cloud)"
            ),
        ] = None,
    ) -> str:
        """Create a new Jira ticket.

        Creates a ticket in the specified project with the given fields.

        ## Authentication Required

        Requires `JIRA_API_TOKEN` and `JIRA_WRITE_ENABLED=true` environment variables.

        ## Returned Data

        Returns a JSON object with:
        - **key**: Created ticket key (e.g., CILAB-1234)
        - **summary**: Ticket summary
        - **url**: Direct link to the ticket

        Returns:
            JSON string with created ticket data
        """
        try:
            project_key = project_key.strip().upper()
            jira_service = JiraService()
            result = jira_service.create_issue(
                project_key=project_key,
                summary=summary,
                description=description,
                issue_type=issue_type,
                priority=priority,
                labels=labels,
                components=components,
                assignee=assignee,
            )
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def update_jira_ticket(
        ticket_key: Annotated[
            str,
            Field(
                description="Jira ticket key in format PROJECT-NUMBER (e.g., CILAB-1234)"
            ),
        ],
        summary: Annotated[
            str | None,
            Field(description="New summary/title for the ticket"),
        ] = None,
        description: Annotated[
            str | None,
            Field(description="New description (supports Jira wiki markup)"),
        ] = None,
        priority: Annotated[
            str | None,
            Field(
                description="New priority name (e.g., Blocker, Critical, Major, Minor, Trivial)"
            ),
        ] = None,
        labels: Annotated[
            list[str] | None,
            Field(
                description="Labels to set on the ticket. Note: this REPLACES all existing labels."
            ),
        ] = None,
        components: Annotated[
            list[str] | None,
            Field(
                description="Component names to set. Note: this REPLACES all existing components."
            ),
        ] = None,
        assignee: Annotated[
            str | None,
            Field(
                description="New assignee username (Jira Server/DC) or account ID (Jira Cloud)"
            ),
        ] = None,
        transition: Annotated[
            str | None,
            Field(
                description="Workflow transition name to apply (e.g., 'In Progress', 'Done'). Use list_jira_transitions to see available transitions."
            ),
        ] = None,
        custom_fields: Annotated[
            dict[str, str] | None,
            Field(
                description=(
                    "Dictionary of custom field IDs (customfield_NNNNN) or "
                    "human-readable field names to values. Supports Forge/Connect "
                    "app fields (e.g. encrypted select fields). "
                    'Example: {"Escape Reason": "Test doesn\'t exist", '
                    '"customfield_10982": "Stability"}'
                )
            ),
        ] = None,
    ) -> str:
        """Update an existing Jira ticket.

        Updates one or more fields on a ticket. All fields are optional but at least
        one must be provided.

        Note: `labels` and `components` replace existing values entirely (not append).
        Use `list_jira_transitions` to discover available transition names before
        attempting a status change.

        ## Authentication Required

        Requires `JIRA_API_TOKEN` and `JIRA_WRITE_ENABLED=true` environment variables.

        ## Returned Data

        Returns a JSON object with:
        - **key**: Ticket key
        - **status**: "updated"
        - **url**: Direct link to the ticket
        - **rendered_values**: (when custom_fields are set) Human-readable values
          after update, useful for confirming Forge field writes

        Returns:
            JSON string with update result
        """
        try:
            normalized_key = validate_ticket_key(ticket_key)

            # Verify at least one field is provided
            if all(
                v is None
                for v in [
                    summary,
                    description,
                    priority,
                    labels,
                    components,
                    assignee,
                    transition,
                    custom_fields,
                ]
            ):
                return json.dumps(
                    {"error": "At least one field must be provided to update."},
                    indent=2,
                )

            jira_service = JiraService()
            result = jira_service.update_issue(
                ticket_key=normalized_key,
                summary=summary,
                description=description,
                priority=priority,
                labels=labels,
                components=components,
                assignee=assignee,
                transition=transition,
                custom_fields=custom_fields,
            )
            return json.dumps(result, indent=2)
        except ValueError as e:
            return json.dumps({"error": str(e)}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def add_jira_comment(
        ticket_key: Annotated[
            str,
            Field(
                description="Jira ticket key in format PROJECT-NUMBER (e.g., CILAB-1234)"
            ),
        ],
        body: Annotated[
            str,
            Field(description="Comment body text (supports Jira wiki markup)"),
        ],
    ) -> str:
        """Add a comment to a Jira ticket.

        ## Authentication Required

        Requires `JIRA_API_TOKEN` and `JIRA_WRITE_ENABLED=true` environment variables.

        ## Returned Data

        Returns a JSON object with:
        - **comment_id**: ID of the created comment
        - **author**: Comment author display name
        - **created**: Creation timestamp

        Returns:
            JSON string with comment data
        """
        try:
            normalized_key = validate_ticket_key(ticket_key)
            jira_service = JiraService()
            result = jira_service.add_comment(normalized_key, body)
            return json.dumps(result, indent=2)
        except ValueError as e:
            return json.dumps({"error": str(e)}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.tool()
    async def list_jira_transitions(
        ticket_key: Annotated[
            str,
            Field(
                description="Jira ticket key in format PROJECT-NUMBER (e.g., CILAB-1234)"
            ),
        ],
    ) -> str:
        """List available workflow transitions for a Jira ticket.

        Returns the transitions that can be applied to the ticket based on its
        current status and the project's workflow configuration. Use the transition
        names with the `update_jira_ticket` tool to change a ticket's status.

        ## Authentication Required

        Requires `JIRA_API_TOKEN` and `JIRA_WRITE_ENABLED=true` environment variables.

        ## Returned Data

        Returns a JSON array of objects with:
        - **id**: Transition ID
        - **name**: Transition name (use this with update_jira_ticket)

        Returns:
            JSON string with available transitions
        """
        try:
            normalized_key = validate_ticket_key(ticket_key)
            jira_service = JiraService()
            result = jira_service.get_transitions(normalized_key)
            return json.dumps(result, indent=2)
        except ValueError as e:
            return json.dumps({"error": str(e)}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
