"""Broadcom KB search tool for finding knowledge base articles.

This tool searches specifically for Broadcom KB articles from knowledge.broadcom.com domain.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any, Callable, List, Dict

from dotenv import load_dotenv
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import CallToolResult, TextContent, Tool
from openai import OpenAI
from openai.types.responses import ToolParam

from tools.tool_runner import register_tool_category
from utils.tracing import conditional_observe

EXA_MCP_BASE_URL = "https://mcp.exa.ai/mcp"
DEFAULT_MCP_TIMEOUT_SECONDS = 30
DEFAULT_MAX_SEARCH_RESULTS = 3


def _get_exa_mcp_url() -> str:
    """Build the Exa MCP URL with API key query parameter."""
    load_dotenv()
    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        raise RuntimeError("EXA_API_KEY environment variable not set.")
    return f"{EXA_MCP_BASE_URL}?exaApiKey={api_key}"


def _run_async(coro: Any) -> Any:
    """Run an async coroutine from synchronous tool code."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    raise RuntimeError(
        "broadcom_kb_search_tool cannot run inside an active event loop with the current "
        "synchronous tool runner."
    )


def _extract_text_content(result: CallToolResult) -> str:
    """Convert MCP tool result content into plain text."""
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


def _score_kb_relevance(query: str, kb_articles: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """Score KB articles for relevance using LLM."""
    load_dotenv()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Prepare articles for scoring
    articles_text = "\n\n".join([
        f"Article {i+1}:\nTitle: {article.get('title', 'N/A')}\nURL: {article.get('url', 'N/A')}"
        for i, article in enumerate(kb_articles)
    ])
    
    prompt = f"""You are a KB article relevance scorer. Given a user query and a list of KB articles, score each article's relevance from 0-100.

User Query: "{query}"

KB Articles:
{articles_text}

Scoring criteria (be strict):
- 95-100: EXACT match - Article title contains the EXACT same error message/text from the query
- 85-94: Very high match - Article addresses the same specific issue with same product
- 70-84: High relevance - Similar issue, same product, but not exact error message
- 50-69: Medium relevance - Related topic or product
- 0-49: Low relevance - Different issue or product

IMPORTANT: If the query contains a specific error message in quotes, prioritize articles that have that EXACT error message in the title.

Return ONLY a JSON array of scores in order: [score1, score2, ...]
Example: [95, 45, 70]"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a relevance scoring expert. Return only a JSON array of numbers."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=100
        )
        
        scores_text = response.choices[0].message.content.strip()  # type: ignore
        scores = json.loads(scores_text)
        
        # Add scores to articles
        for i, article in enumerate(kb_articles):
            article['relevance_score'] = scores[i] if i < len(scores) else 0
        
        # Sort by relevance score
        kb_articles.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        # Filter to only high relevance (70+)
        return [a for a in kb_articles if a.get('relevance_score', 0) >= 70]
        
    except Exception as e:
        print(f"Error scoring relevance: {e}")
        # Return all articles if scoring fails
        return kb_articles


def _filter_broadcom_results(search_results: str, query: str = "") -> str:
    """Filter search results to extract only relevant Broadcom KB article URLs and titles with relevance scores."""
    try:
        # Try to parse as JSON first
        try:
            data = json.loads(search_results)
            if isinstance(data, dict) and 'results' in data:
                kb_articles = []
                for result in data['results']:
                    url = result.get('url', '')
                    title = result.get('title', 'Untitled')
                    if 'knowledge.broadcom.com' in url:
                        kb_articles.append({'url': url, 'title': title})
                
                if kb_articles and query:
                    # Score articles for relevance
                    relevant_articles = _score_kb_relevance(query, kb_articles)
                    
                    if relevant_articles:
                        # Return top 2 most relevant with relevance scores
                        kb_links = [f"• [{a['title']}]({a['url']}) [Relevance: {a.get('relevance_score', 0)}%]" for a in relevant_articles[:2]]
                        return "\n\n".join(kb_links)
                    else:
                        return "No highly relevant Broadcom KB articles found (relevance threshold: 70%)"
                elif kb_articles:
                    # No query for scoring, return top 2
                    kb_links = [f"• [{a['title']}]({a['url']})" for a in kb_articles[:2]]
                    return "\n\n".join(kb_links)
                else:
                    return "No Broadcom KB articles found"
        except json.JSONDecodeError:
            pass
        
        # Fallback: text-based URL extraction
        urls = re.findall(r'https://knowledge\.broadcom\.com/[^\s\)]+', search_results)
        
        if urls:
            # Remove duplicates while preserving order
            seen = set()
            unique_urls = []
            for url in urls:
                if url not in seen:
                    seen.add(url)
                    unique_urls.append(url)
            
            # If we have a query, try to score these URLs
            if query and unique_urls:
                # Create article objects with URLs
                kb_articles = [{'url': url, 'title': f"KB Article {url.split('/')[-2] if '/' in url else 'Unknown'}"} for url in unique_urls[:5]]
                
                try:
                    # Score articles for relevance
                    relevant_articles = _score_kb_relevance(query, kb_articles)
                    
                    if relevant_articles:
                        # Return with relevance scores
                        kb_links = [f"• [{a['title']}]({a['url']}) [Relevance: {a.get('relevance_score', 0)}%]" for a in relevant_articles[:2]]
                        return "\n\n".join(kb_links)
                except Exception as e:
                    print(f"Error scoring fallback URLs: {e}")
            
            # Format as plain markdown links without scores
            kb_links = [f"• {url}" for url in unique_urls[:2]]  # Top 2 only
            return "\n\n".join(kb_links)
        else:
            return "No Broadcom KB articles found from knowledge.broadcom.com domain."
            
    except Exception as e:
        return f"Error filtering results: {str(e)}\n\nOriginal results:\n{search_results}"


def _score_tool_name(tool_name: str) -> tuple[int, int]:
    """Score remote MCP tool names to prefer search-oriented tools."""
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
    """Select the most appropriate remote search tool from Exa MCP."""
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
    """Build arguments for the selected Exa MCP search tool."""
    schema = getattr(tool, "inputSchema", {}) or {}
    properties = schema.get("properties", {})
    
    arguments: dict[str, Any] = {}
    
    # Add domain filter for Broadcom
    enhanced_query = f"{query} site:knowledge.broadcom.com"
    
    if "query" in properties:
        arguments["query"] = enhanced_query
    elif "search_term" in properties:
        arguments["search_term"] = enhanced_query
    elif "q" in properties:
        arguments["q"] = enhanced_query
    
    if "num_results" in properties:
        arguments["num_results"] = max_results
    elif "max_results" in properties:
        arguments["max_results"] = max_results
    elif "limit" in properties:
        arguments["limit"] = max_results
    
    if not arguments:
        arguments["query"] = enhanced_query
    
    return arguments


async def _broadcom_kb_search_async(query: str, max_results: int = DEFAULT_MAX_SEARCH_RESULTS) -> str:
    """Execute a Broadcom KB search through Exa's remote MCP server."""
    server_url = _get_exa_mcp_url()
    
    try:
        try:
            async with asyncio.timeout(DEFAULT_MCP_TIMEOUT_SECONDS):
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
                        f"Broadcom KB search returned an error for query '{query}'.\n"
                        f"{_extract_text_content(result)}"
                    )
                
                raw_results = _extract_text_content(result)
                filtered_results = _filter_broadcom_results(raw_results, query)
                
                return (
                    f"Broadcom KB search results for '{query}':\n"
                    f"{filtered_results}"
                )
        except AttributeError:
            # Fallback for Python < 3.11
            async def _do_search():
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
                        
                        return await session.call_tool(tool_name, tool_arguments)
            
            result = await asyncio.wait_for(_do_search(), timeout=DEFAULT_MCP_TIMEOUT_SECONDS)
            
            if result.isError:
                return (
                    f"Broadcom KB search returned an error for query '{query}'.\n"
                    f"{_extract_text_content(result)}"
                )
            
            raw_results = _extract_text_content(result)
            filtered_results = _filter_broadcom_results(raw_results, query)
            
            return (
                f"Broadcom KB search results for '{query}':\n"
                f"{filtered_results}"
            )
    except asyncio.TimeoutError:
        return (
            f"Broadcom KB search timed out after {DEFAULT_MCP_TIMEOUT_SECONDS} seconds for query '{query}'. "
            "The Exa MCP server may be unavailable or slow to respond."
        )
    except Exception as e:
        return (
            f"Broadcom KB search failed for query '{query}': {type(e).__name__}: {str(e)}"
        )


@conditional_observe(
    name="broadcom_kb_search",
    as_type="tool",
    capture_input=True,
    capture_output=True,
)
def broadcom_kb_search(query: str, max_results: int = DEFAULT_MAX_SEARCH_RESULTS) -> str:
    """Search for Broadcom KB articles from knowledge.broadcom.com.
    
    Args:
        query: Search query for KB articles
        max_results: Maximum number of results to request
    
    Returns:
        Search results filtered to only Broadcom KB articles
    """
    print(f"\n[TOOL: broadcom_kb_search] Searching Broadcom KB for '{query}'...")
    return _run_async(_broadcom_kb_search_async(query=query, max_results=max_results))


BROADCOM_KB_TOOLS: list[ToolParam] = [
    {
        "type": "function",
        "name": "broadcom_kb_search",
        "description": (
            "Search for Broadcom knowledge base articles from knowledge.broadcom.com. "
            "Use this when the user needs information, documentation, or guidance about "
            "VMware/Broadcom products, features, or troubleshooting steps. Returns KB "
            "articles with titles, URLs, and summaries."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "The search query for KB articles. Include product names, "
                        "feature names, or technical terms for better results."
                    ),
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of KB articles to return.",
                    "minimum": 1,
                    "maximum": 5,
                    "default": 3,
                },
            },
            "required": ["query", "max_results"],
            "additionalProperties": False,
        },
    }
]


BROADCOM_KB_FUNCTIONS: dict[str, Callable[..., str]] = {
    "broadcom_kb_search": broadcom_kb_search,
}

register_tool_category(BROADCOM_KB_FUNCTIONS)

# Made with Bob