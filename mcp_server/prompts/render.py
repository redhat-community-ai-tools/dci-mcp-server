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

"""Render MCP prompts outside of an MCP server context.

Provides ``render_prompt`` (async) and ``list_prompts`` (sync) for use
by CLI tools and integration tests.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..config import has_dci_credentials
from .prompts import register_prompts

has_dci_credentials()

PromptFn = Callable[..., Any]


def _collect_prompts() -> dict[str, PromptFn]:
    """Register prompts on a lightweight stub and return the captured functions."""
    captured: dict[str, PromptFn] = {}

    class _FakeMCP:
        @staticmethod
        def prompt():
            def decorator(fn):
                captured[fn.__name__] = fn
                return fn

            return decorator

    register_prompts(_FakeMCP())
    return captured


def list_prompts() -> list[str]:
    """Return the names of all registered prompts."""
    return sorted(_collect_prompts())


async def render_prompt(name: str, **kwargs: str) -> str:
    """Render a prompt by name with the given keyword arguments.

    Raises:
        ValueError: If *name* does not match any registered prompt.
    """
    prompts = _collect_prompts()
    fn = prompts.get(name)
    if fn is None:
        available = ", ".join(sorted(prompts))
        raise ValueError(f"Unknown prompt {name!r}. Available prompts: {available}")
    return await fn(**kwargs)


# render.py ends here
