"""Tools package for agent functionality.

This package contains:
- websearch_tools.py: Remote Exa MCP-backed web search tools
- rag_incident_tool.py: RAG-based incident search tool
- broadcom_kb_search_tool.py: Broadcom KB article search tool
- kb_content_fetcher.py: KB article content extraction
- git_data_fetcher.py: Git-based operational signals fetcher
- tool_runner.py: Generic tool execution logic

Tool categories can be added as separate modules to maintain clear separation
and scalability.
"""

from tools.tool_runner import execute_tool_call

try:
    from tools.rag_incident_tool import RAG_INCIDENT_TOOLS
except Exception:
    RAG_INCIDENT_TOOLS = []

try:
    from tools.broadcom_kb_search_tool import BROADCOM_KB_TOOLS
except Exception:
    BROADCOM_KB_TOOLS = []

ALL_TOOLS = [*RAG_INCIDENT_TOOLS, *BROADCOM_KB_TOOLS]

__all__ = [
    "ALL_TOOLS",
    "RAG_INCIDENT_TOOLS",
    "BROADCOM_KB_TOOLS",
    "execute_tool_call",
]
