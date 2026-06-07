#
# Copyright (C) 2026 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""CLI entry point for rendering MCP prompts.

Usage::

    python -m mcp_server.prompts --list
    python -m mcp_server.prompts rca dci_job_id=<job-id>
    python -m mcp_server.prompts weekly subject=test-team
"""

from __future__ import annotations

import asyncio
import sys

from .render import list_prompts, render_prompt


def main() -> None:
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print("Usage: python -m mcp_server.prompts [--list] <name> [key=value ...]")
        print()
        print("Options:")
        print("  --list    List available prompt names")
        print()
        print("Examples:")
        print("  python -m mcp_server.prompts --list")
        print("  python -m mcp_server.prompts rca dci_job_id=<job-id>")
        print("  python -m mcp_server.prompts weekly subject=test-team")
        sys.exit(0)

    if args[0] == "--list":
        for name in list_prompts():
            print(name)
        sys.exit(0)

    name = args[0]
    kwargs: dict[str, str] = {}
    for arg in args[1:]:
        if "=" not in arg:
            print(
                f"Error: argument {arg!r} must be in key=value format", file=sys.stderr
            )
            sys.exit(1)
        key, value = arg.split("=", 1)
        kwargs[key] = value

    try:
        result = asyncio.run(render_prompt(name, **kwargs))
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(result)


if __name__ == "__main__":
    main()


# __main__.py ends here
