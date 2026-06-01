"""Evaluation tests for MCP tool selection using claude -p.

These tests verify that Claude correctly selects and uses MCP tools
when given natural language prompts. They run the full stack: Claude's
reasoning, tool selection, query construction, and MCP tool execution.

Eval cases are conditionally skipped based on .env credentials.
Run with: uv run pytest -m eval -v
Override model with: EVAL_MODEL=haiku uv run pytest -m eval -v
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Load .env for credential checks
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env", override=True)

CREDENTIAL_CHECKS = {
    "date": lambda: True,
    "dci": lambda: bool(
        (os.getenv("DCI_CLIENT_ID") and os.getenv("DCI_API_SECRET"))
        or (os.getenv("DCI_LOGIN") and os.getenv("DCI_PASSWORD"))
    ),
    "jira": lambda: bool(os.getenv("JIRA_API_TOKEN")),
    "github": lambda: bool(os.getenv("GITHUB_TOKEN")),
    "gitlab": lambda: bool(os.getenv("GITLAB_TOKEN")),
    "support_case": lambda: bool(os.getenv("OFFLINE_TOKEN")),
}


def has_claude_cli():
    return shutil.which("claude") is not None


def run_eval(prompt, allowed_tools):
    """Run claude -p with MCP server and return parsed JSON messages."""
    mcp_config = json.dumps(
        {
            "mcpServers": {
                "dci": {
                    "command": "uv",
                    "args": ["run", "main.py"],
                    "cwd": str(project_root),
                }
            }
        }
    )

    cmd = [
        "claude",
        "-p",
        prompt,
        "--output-format",
        "stream-json",
        "--verbose",
        "--model",
        os.getenv("EVAL_MODEL", "sonnet"),
        "--no-session-persistence",
        "--bare",
        "--strict-mcp-config",
        "--dangerously-skip-permissions",
        "--max-budget-usd",
        "0.50",
        "--mcp-config",
        mcp_config,
        "--allowed-tools",
        *allowed_tools,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(project_root),
        )
    except subprocess.TimeoutExpired:
        pytest.skip("claude -p timed out (300s)")

    messages = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            messages.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    if result.returncode != 0:
        # Extract error from the result message in stream-json output
        error_msg = ""
        for msg in messages:
            if msg.get("type") == "result":
                error_msg = msg.get("result", "")
                break
        if not error_msg:
            error_msg = result.stderr or "(no error details)"
        pytest.fail(f"claude -p failed (rc={result.returncode}): {error_msg[:500]}")

    return messages


def extract_tool_calls(messages):
    """Extract tool call names and inputs from verbose JSON output."""
    tool_calls = []
    for msg in messages:
        if msg.get("type") != "assistant":
            continue
        content = msg.get("message", {}).get("content", [])
        for block in content:
            if block.get("type") == "tool_use":
                tool_calls.append(
                    {"name": block["name"], "input": block.get("input", {})}
                )
    return tool_calls


def extract_final_answer(messages):
    """Extract the final text response."""
    for msg in reversed(messages):
        if msg.get("type") == "result":
            return msg.get("result", "")
    return ""


def extract_result(messages):
    """Extract the result message."""
    for msg in messages:
        if msg.get("type") == "result":
            return msg
    return {}


EVAL_CASES = [
    {
        "id": "today_date",
        "prompt": "What is today's date? Use a tool to find out.",
        "requires": "date",
        "allowed_tools": ["mcp__dci__today", "mcp__dci__now"],
        "expected_tools": ["mcp__dci__today"],
        "answer_contains": ["202"],
    },
    {
        "id": "search_failed_jobs",
        "prompt": (
            "Search for DCI jobs with status failure, limit to 5 results. "
            "Return the job IDs."
        ),
        "requires": "dci",
        "allowed_tools": ["mcp__dci__search_dci_jobs"],
        "expected_tools": ["mcp__dci__search_dci_jobs"],
        "expected_params": {"query": "failure"},
    },
    {
        "id": "dci_job_by_id",
        "prompt": (
            "Get the DCI job with ID 8e481709-b14c-4ab6-9b56-e093fdab4f6e. "
            "Return its name and status."
        ),
        "requires": "dci",
        "allowed_tools": ["mcp__dci__search_dci_jobs"],
        "expected_tools": ["mcp__dci__search_dci_jobs"],
        "expected_params": {"query": "8e481709-b14c-4ab6-9b56-e093fdab4f6e"},
        "answer_contains": ["pv-tests"],
    },
    {
        "id": "dci_components",
        "prompt": "List active OCP components in DCI, limit to 5 results.",
        "requires": "dci",
        "allowed_tools": ["mcp__dci__query_dci_components"],
        "expected_tools": ["mcp__dci__query_dci_components"],
    },
    {
        "id": "dci_teams",
        "prompt": "List all DCI teams, limit to 5.",
        "requires": "dci",
        "allowed_tools": ["mcp__dci__query_dci_teams"],
        "expected_tools": ["mcp__dci__query_dci_teams"],
    },
    {
        "id": "dci_remotecis",
        "prompt": "List DCI remotecis, limit to 5.",
        "requires": "dci",
        "allowed_tools": ["mcp__dci__query_dci_remotecis"],
        "expected_tools": ["mcp__dci__query_dci_remotecis"],
    },
    {
        "id": "jira_ticket",
        "prompt": "Get the details of Jira ticket CILAB-1.",
        "requires": "jira",
        "allowed_tools": [
            "mcp__dci__get_jira_ticket",
            "mcp__dci__search_jira_tickets",
        ],
        "expected_tools": ["mcp__dci__get_jira_ticket"],
        "expected_params": {"ticket_key": "CILAB-1"},
    },
    {
        "id": "jira_search",
        "prompt": "Search for tickets in the CILAB Jira project, limit to 5.",
        "requires": "jira",
        "allowed_tools": [
            "mcp__dci__search_jira_tickets",
            "mcp__dci__get_jira_ticket",
            "mcp__dci__count_jira_tickets",
        ],
        "expected_tools": ["mcp__dci__search_jira_tickets"],
        "expected_params": {"jql": "CILAB"},
    },
    {
        "id": "github_repo",
        "prompt": (
            "Get information about the GitHub repository "
            "redhat-community-ai-tools/dci-mcp-server."
        ),
        "requires": "github",
        "allowed_tools": [
            "mcp__dci__get_github_repository_info",
            "mcp__dci__search_github_issues",
        ],
        "expected_tools": ["mcp__dci__get_github_repository_info"],
        "expected_params": {"repo": "redhat-community-ai-tools/dci-mcp-server"},
    },
]


skip_no_claude = pytest.mark.skipif(
    not has_claude_cli(), reason="claude CLI not available"
)


@pytest.mark.eval
@skip_no_claude
@pytest.mark.parametrize(
    "eval_case",
    EVAL_CASES,
    ids=[c["id"] for c in EVAL_CASES],
)
def test_eval(eval_case):
    requires = eval_case["requires"]
    if not CREDENTIAL_CHECKS[requires]():
        pytest.skip(f"Missing credentials for {requires}")

    messages = run_eval(eval_case["prompt"], eval_case["allowed_tools"])
    result = extract_result(messages)

    # Check no error
    assert not result.get("is_error"), (
        f"Eval returned error: {result.get('result', '')}"
    )

    # Check num_turns (default max 2: one tool call + final answer)
    max_turns = eval_case.get("max_turns", 2)
    num_turns = result.get("num_turns", 0)
    assert num_turns <= max_turns, (
        f"Too many turns: {num_turns} (max {max_turns}). "
        f"Claude likely retried due to a bad query or unclear tool description."
    )

    # Check tool selection
    tool_calls = extract_tool_calls(messages)
    called_names = [tc["name"] for tc in tool_calls]
    for expected in eval_case["expected_tools"]:
        assert expected in called_names, (
            f"Expected tool {expected} not called. Called: {called_names}"
        )

    # Check parameter values (substring match in serialized input)
    if "expected_params" in eval_case:
        for tool_call in tool_calls:
            if tool_call["name"] in eval_case["expected_tools"]:
                input_str = json.dumps(tool_call["input"])
                for key, expected_val in eval_case["expected_params"].items():
                    assert expected_val.lower() in input_str.lower(), (
                        f"Expected '{expected_val}' in {key} param of "
                        f"{tool_call['name']}, got: {input_str}"
                    )

    # Check answer content
    if "answer_contains" in eval_case:
        answer = extract_final_answer(messages)
        for expected in eval_case["answer_contains"]:
            assert expected.lower() in answer.lower(), (
                f"Expected '{expected}' in answer, got: {answer[:200]}"
            )

    # Report cost and turns
    cost = result.get("total_cost_usd", 0)
    print(f"  [eval] {eval_case['id']}: ${cost:.4f} ({num_turns} turns)")
