"""Web search tools backed by Exa's remote MCP server.

This module exposes a standard callable tool for the existing OpenAI Responses
workflow. Internally, it connects to Exa's remote MCP endpoint over streamable
HTTP, discovers the available remote tools, selects a suitable search tool, and
returns a formatted text result to the model.

The implementation is intentionally isolated from the nutrition-specific tools
so the remote MCP integration remains modular and reusable.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Callable

from dotenv import load_dotenv
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import CallToolResult, TextContent, Tool
from openai.types.responses import ToolParam

from tools.tool_runner import register_tool_category
from utils.tracing import conditional_observe

EXA_MCP_BASE_URL = "https://mcp.exa.ai/mcp"
DEFAULT_MCP_TIMEOUT_SECONDS = 90
DEFAULT_MAX_SEARCH_RESULTS = 5


def _get_exa_mcp_url() -> str:
    """Build the Exa MCP URL with API key query parameter.

    Returns:
        Fully qualified Exa MCP URL including the API key.

    Raises:
        RuntimeError: If EXA_API_KEY is not configured.
    """
    load_dotenv()

    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        raise RuntimeError("EXA_API_KEY environment variable not set.")

    return f"{EXA_MCP_BASE_URL}?exaApiKey={api_key}"


def _run_async(coro: Any) -> Any:
    """Run an async coroutine from synchronous tool code.

    This helper supports the current synchronous tool execution flow used by the
    OpenAI Responses API integration.

    Args:
        coro: Coroutine object to execute.

    Returns:
        Result of the awaited coroutine.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    raise RuntimeError(
        "websearch_tool cannot run inside an active event loop with the current "
        "synchronous tool runner."
    )


def _extract_text_content(result: CallToolResult) -> str:
    """Convert MCP tool result content into plain text.

    Args:
        result: MCP call tool result.

    Returns:
        Human-readable text representation of the result.
    """
    formatted_parts: list[str] = []

    for item in result.content:
        if isinstance(item, TextContent):
            formatted_parts.append(item.text)
            continue

        text_value = getattr(item, "text", None)
        if isinstance(text_value, str) and text_value.strip():
            formatted_parts.append(text_value)
            continue

        serialized = None
        if hasattr(item, "model_dump"):
            serialized = item.model_dump()
        elif hasattr(item, "dict"):
            serialized = item.dict()

        if serialized:
            formatted_parts.append(json.dumps(serialized, ensure_ascii=False, indent=2))

    if result.structuredContent:
        formatted_parts.append(
            "Structured content:\n"
            + json.dumps(result.structuredContent, ensure_ascii=False, indent=2)
        )

    if not formatted_parts:
        return "The Exa MCP server returned no readable content."

    return "\n\n".join(part for part in formatted_parts if part.strip())


def _score_tool_name(tool_name: str) -> tuple[int, int]:
    """Score remote MCP tool names to prefer search-oriented tools.

    Args:
        tool_name: Remote MCP tool name.

    Returns:
        Tuple used for sorting. Lower is better.
    """
    normalized = tool_name.lower()

    if normalized == "web_search_exa":
        return (0, len(normalized))
    if "search" in normalized and "exa" in normalized:
        return (1, len(normalized))
    if "search" in normalized:
        return (2, len(normalized))
    if "web" in normalized or "find" in normalized:
        return (3, len(normalized))

    return (10, len(normalized))


def _select_search_tool(tools: list[Tool]) -> Tool:
    """Select the most appropriate remote search tool from Exa MCP.

    Args:
        tools: Tools exposed by the remote MCP server.

    Returns:
        Selected MCP tool definition.

    Raises:
        RuntimeError: If no suitable search tool is available.
    """
    if not tools:
        raise RuntimeError("No tools were exposed by the Exa MCP server.")

    ranked_tools = sorted(
        tools,
        key=lambda tool: _score_tool_name(getattr(tool, "name", "")),
    )

    selected_tool = ranked_tools[0]
    selected_name = getattr(selected_tool, "name", "")

    if _score_tool_name(selected_name)[0] >= 10:
        available = ", ".join(getattr(tool, "name", "<unknown>") for tool in tools)
        raise RuntimeError(
            "No search-capable tool was found on the Exa MCP server. "
            f"Available tools: {available}"
        )

    return selected_tool


def _build_search_arguments(tool: Tool, query: str, max_results: int) -> dict[str, Any]:
    """Build arguments for the selected Exa MCP search tool.

    Args:
        tool: Selected remote MCP tool.
        query: Search query.
        max_results: Desired maximum number of results.

    Returns:
        Arguments dictionary compatible with the remote tool schema.
    """
    schema = getattr(tool, "inputSchema", {}) or {}
    properties = schema.get("properties", {})

    arguments: dict[str, Any] = {}

    if "query" in properties:
        arguments["query"] = query
    elif "search_term" in properties:
        arguments["search_term"] = query
    elif "q" in properties:
        arguments["q"] = query

    if "num_results" in properties:
        arguments["num_results"] = max_results
    elif "max_results" in properties:
        arguments["max_results"] = max_results
    elif "limit" in properties:
        arguments["limit"] = max_results

    if not arguments:
        arguments["query"] = query

    return arguments


async def _websearch_tool_async(query: str, max_results: int = DEFAULT_MAX_SEARCH_RESULTS) -> str:
    """Execute a web search through Exa's remote MCP server.

    Args:
        query: Search query to send to Exa.
        max_results: Maximum number of results to request.

    Returns:
        Formatted search results as plain text.
    """
    server_url = _get_exa_mcp_url()

    async with streamable_http_client(server_url) as (
        read_stream,
        write_stream,
        _get_session_id,
    ):
        session = ClientSession(read_stream, write_stream)
        async with session:
            await session.initialize()

            available_tools = await session.list_tools()
            selected_tool = _select_search_tool(available_tools.tools)
            tool_name = getattr(selected_tool, "name", "")

            tool_arguments = _build_search_arguments(
                tool=selected_tool,
                query=query,
                max_results=max_results,
            )

            result = await session.call_tool(tool_name, tool_arguments)

    if result.isError:
        return (
            f"Exa web search returned an error for query '{query}'.\n"
            f"{_extract_text_content(result)}"
        )

    return (
        f"Web search results for '{query}':\n"
        f"{_extract_text_content(result)}"
    )


@conditional_observe(
    name="websearch_tool",
    as_type="tool",
    capture_input=True,
    capture_output=True,
)
def websearch_tool(query: str, max_results: int = DEFAULT_MAX_SEARCH_RESULTS) -> str:
    """Search the web using Exa's remote MCP server.

    Args:
        query: Search query.
        max_results: Maximum number of results to request.

    Returns:
        Search results formatted as text.
    """
    print(f"Searching the web for '{query}'...")
    return _run_async(_websearch_tool_async(query=query, max_results=max_results))


WEBSEARCH_TOOLS: list[ToolParam] = [
    {
        "type": "function",
        "name": "websearch_tool",
        "description": (
            "Search the web for nutrition information, calorie references, "
            "food facts, and broader diet-related questions when local data is "
            "missing, weak, ambiguous, or insufficient."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "The web search query. Include the food item or nutrition "
                        "question and enough context to retrieve reliable results."
                    ),
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of search results to request.",
                    "minimum": 1,
                    "maximum": 10,
                    "default": 5,
                },
            },
            "required": ["query", "max_results"],
            "additionalProperties": False,
        },
    }
]


WEBSEARCH_FUNCTIONS: dict[str, Callable[..., str]] = {
    "websearch_tool": websearch_tool,
}

register_tool_category(WEBSEARCH_FUNCTIONS)

# Made with Bob
