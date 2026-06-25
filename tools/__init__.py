"""Tools package for agent functionality.

This package contains:
- nutrition_tools.py: Nutrition-specific local lookup tools (legacy)
- websearch_tools.py: Remote Exa MCP-backed web search tools
- rag_incident_tool.py: RAG-based incident search tool
- broadcom_kb_search_tool.py: Broadcom KB article search tool
- tool_runner.py: Generic tool execution logic

Tool categories can be added as separate modules to maintain clear separation
and scalability. Each category module should contain:
- Tool function implementations
- OpenAI tool schemas
- Function registry for that category
"""

from tools.tool_runner import execute_tool_call

# Import tools conditionally to avoid errors
try:
    from tools.nutrition_tools import NUTRITION_TOOLS
except Exception:
    NUTRITION_TOOLS = []

try:
    from tools.websearch_tools import WEBSEARCH_TOOLS
except Exception:
    WEBSEARCH_TOOLS = []

try:
    from tools.rag_incident_tool import RAG_INCIDENT_TOOLS
except Exception:
    RAG_INCIDENT_TOOLS = []

try:
    from tools.broadcom_kb_search_tool import BROADCOM_KB_TOOLS
except Exception:
    BROADCOM_KB_TOOLS = []

ALL_TOOLS = [*NUTRITION_TOOLS, *WEBSEARCH_TOOLS, *RAG_INCIDENT_TOOLS, *BROADCOM_KB_TOOLS]

__all__ = [
    "ALL_TOOLS",
    "NUTRITION_TOOLS",
    "WEBSEARCH_TOOLS",
    "RAG_INCIDENT_TOOLS",
    "BROADCOM_KB_TOOLS",
    "execute_tool_call",
]
