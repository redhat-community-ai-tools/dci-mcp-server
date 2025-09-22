# Jira Integration Setup

This document explains how to set up and use the Jira integration in the DCI MCP Server for collecting ticket data.

## Overview

The Jira integration provides tools to:
- Retrieve comprehensive ticket data including comments and changelog
- Search tickets using JQL (Jira Query Language)
- Get project information
- Extract Jira ticket references from DCI job comments

## Prerequisites

- Access to Red Hat Jira at https://issues.redhat.com
- A Red Hat account with Jira access
- Python environment with the DCI MCP Server installed

## Getting Your Jira API Token

### Step 1: Access Your Profile

1. Go to [https://issues.redhat.com/secure/ViewProfile.jspa](https://issues.redhat.com/secure/ViewProfile.jspa)
2. Log in with your Red Hat credentials if prompted

### Step 2: Create a Personal Access Token

1. In your profile page, look for "Personal Access Tokens" in the left sidebar
2. Click on "Personal Access Tokens"
3. Click the "Create token" button
4. Fill in the token details:
   - **Name**: Give your token a descriptive name (e.g., "DCI MCP Server")
   - **Expiration**: Set an expiration date (optional but recommended for security)
   - **Scopes**: Select the appropriate scopes (typically "read" access is sufficient)
5. Click "Create"
6. **Important**: Copy the generated token immediately - it won't be shown again!

### Step 3: Configure Environment Variables

Add the following to your `.env` file:

```bash
# Jira Integration
JIRA_API_TOKEN=your_generated_token_here
JIRA_URL=https://issues.redhat.com
```

## Available Tools

### 1. Get Jira Ticket Data

Retrieve comprehensive information about a specific ticket:

```python
# Example usage
ticket_data = await get_jira_ticket("CILAB-1234", max_comments=10)
```

**Parameters:**
- `ticket_key`: Jira ticket key (e.g., "CILAB-1234", "OCP-5678")
- `max_comments`: Maximum number of comments to retrieve (default: 10, max: 50)

**Returns:**
- Basic ticket information (summary, description, status, priority, etc.)
- Date information (created, updated)
- People information (assignee, reporter)
- Classification (labels, components, versions)
- Recent comments with author and timestamps
- Changelog/history of changes
- Direct URL to the ticket

### 2. Search Jira Tickets

Search for tickets using JQL (Jira Query Language):

```python
# Example usage
tickets = await search_jira_tickets("project = CILAB AND status = Open", max_results=50)
```

**Parameters:**
- `jql`: JQL query string
- `max_results`: Maximum number of results (default: 50, max: 200)

**JQL Examples:**
- `project = CILAB` - All tickets in CILAB project
- `status = Open` - All open tickets
- `assignee = currentUser()` - Tickets assigned to you
- `created >= -7d` - Tickets created in the last 7 days
- `text ~ "openshift"` - Tickets containing "openshift" in text fields

### 3. Get Project Information

Retrieve basic information about a Jira project:

```python
# Example usage
project_info = await get_jira_project_info("CILAB")
```

**Parameters:**
- `project_key`: Project key (e.g., "CILAB", "OCP", "RHEL")

## Integration with DCI Jobs

The Jira integration works seamlessly with DCI job data. You can:

1. **Extract Jira tickets from job comments:**
   ```python
   # Search for jobs with CILAB tickets
   jobs = await search_dci_jobs("comment=~'.*CILAB.*'")
   
   # Extract ticket keys from comments
   for job in jobs:
       if job.get('comment'):
           ticket_key = job['comment']  # e.g., "CILAB-1234"
           ticket_data = await get_jira_ticket(ticket_key)
   ```

2. **Find jobs related to specific Jira tickets:**
   ```python
   # Search for jobs mentioning a specific ticket
   jobs = await search_dci_jobs(f"comment='CILAB-1234'")
   ```

## Common Use Cases

### 1. Investigate Failed Jobs

When a DCI job fails with a Jira ticket reference:

```python
# Get the job details
job = await search_dci_jobs("id='job-id-here'")

# Extract the Jira ticket from the comment
ticket_key = job['comment']  # e.g., "CILAB-1234"

# Get detailed ticket information
ticket_data = await get_jira_ticket(ticket_key)

# Analyze the ticket for context about the failure
print(f"Ticket: {ticket_data['summary']}")
print(f"Status: {ticket_data['status']}")
print(f"Description: {ticket_data['description']}")
```

### 2. Monitor Project Progress

Track tickets in a specific project:

```python
# Get all open CILAB tickets
open_tickets = await search_jira_tickets("project = CILAB AND status = Open")

# Get tickets assigned to you
my_tickets = await search_jira_tickets("assignee = currentUser() AND status != Closed")
```

### 3. Analyze Ticket History

Examine the changelog and comments for a ticket:

```python
ticket_data = await get_jira_ticket("CILAB-1234", max_comments=20)

# Review recent comments
for comment in ticket_data['comments']:
    print(f"{comment['author']}: {comment['body']}")
    print(f"Date: {comment['created']}")

# Review changelog
for change in ticket_data['changelog']:
    print(f"Changed by: {change['author']}")
    print(f"Date: {change['created']}")
    for item in change['items']:
        print(f"  {item['field']}: {item['from_string']} -> {item['to_string']}")
```

## Security Considerations

- **Token Security**: Keep your Jira API token secure and never commit it to version control
- **Token Expiration**: Set appropriate expiration dates for your tokens
- **Scope Limitation**: Use the minimum required scopes for your use case
- **Environment Variables**: Store credentials in `.env` file and ensure it's in `.gitignore`

## Troubleshooting

### Common Issues

1. **Authentication Error**: 
   - Verify your `JIRA_API_TOKEN` and `JIRA_EMAIL` are correct
   - Ensure your token hasn't expired
   - Check that your account has access to the Jira instance

2. **Ticket Not Found**:
   - Verify the ticket key format (PROJECT-NUMBER)
   - Ensure the ticket exists and you have access to it
   - Check that the project key is correct

3. **Permission Denied**:
   - Verify your account has read access to the tickets/projects
   - Check if the ticket is restricted to specific users/groups

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## API Rate Limits

Be aware of Jira API rate limits:
- Red Hat Jira typically allows 1000 requests per hour per user
- The tools include built-in rate limiting and retry logic
- For high-volume usage, consider implementing additional rate limiting

## Support

For issues with the Jira integration:
1. Check the troubleshooting section above
2. Verify your environment variables are set correctly
3. Test with a simple ticket query first
4. Check the DCI MCP Server logs for detailed error messages
