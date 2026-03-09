#!/usr/bin/env python3
"""Quick smoke test for Jira integration tools."""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

env_file = Path(__file__).parent / ".env"
load_dotenv(env_file, override=True)

sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.services.jira_service import JiraService


def test_get_project_info(service: JiraService, project_key: str = "CILAB"):
    print(f"\n{'='*60}")
    print(f"1. get_jira_project_info('{project_key}')")
    print("=" * 60)
    result = service.get_project_info(project_key)
    print(json.dumps(result, indent=2))
    return result


def test_search_tickets(service: JiraService, jql: str = "project = CILAB AND status = Open", max_results: int = 5):
    print(f"\n{'='*60}")
    print(f"2. search_jira_tickets('{jql}', max_results={max_results})")
    print("=" * 60)
    result = service.search_tickets(jql, max_results)
    print(json.dumps(result, indent=2))
    return result


def test_get_ticket(service: JiraService, ticket_key: str, max_comments: int = 3):
    print(f"\n{'='*60}")
    print(f"3. get_jira_ticket('{ticket_key}', max_comments={max_comments})")
    print("=" * 60)
    result = service.get_ticket_data(ticket_key, max_comments)
    print(json.dumps(result, indent=2))
    return result


def main():
    print("Jira Integration Smoke Test")
    print("=" * 60)

    try:
        service = JiraService()
        print("Connected to Jira successfully.")
    except Exception as e:
        print(f"Failed to connect: {e}")
        sys.exit(1)

    # 1. Search tickets with a broad query to find accessible projects
    ticket_key = None
    try:
        tickets = test_search_tickets(
            service, "assignee = currentUser() ORDER BY updated DESC", max_results=5
        )
        if tickets:
            ticket_key = tickets[0]["key"]
            project_key = ticket_key.split("-")[0]
        else:
            tickets = test_search_tickets(
                service, "updated >= -7d ORDER BY updated DESC", max_results=5
            )
            if tickets:
                ticket_key = tickets[0]["key"]
                project_key = ticket_key.split("-")[0]
            else:
                project_key = None
    except Exception as e:
        print(f"  ERROR: {e}")
        project_key = None

    # 2. Project info (using project discovered from search)
    if project_key:
        try:
            test_get_project_info(service, project_key)
        except Exception as e:
            print(f"  ERROR: {e}")
    else:
        print("\nSkipping get_jira_project_info — no project discovered.")

    # 3. Get a single ticket (use first result from search, or fallback)
    if ticket_key:
        try:
            test_get_ticket(service, ticket_key, max_comments=3)
        except Exception as e:
            print(f"  ERROR: {e}")
    else:
        print("\nSkipping get_jira_ticket — no ticket found from search.")

    print(f"\n{'='*60}")
    print("Done.")


if __name__ == "__main__":
    main()
