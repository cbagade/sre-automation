"""Tools package for agent functionality.

This package contains:
- nutrition_tools.py: Nutrition-specific local lookup tools
- websearch_tools.py: Remote Exa MCP-backed web search tools
- tool_runner.py: Generic tool execution logic

Tool categories can be added as separate modules to maintain clear separation
and scalability. Each category module should contain:
- Tool function implementations
- OpenAI tool schemas
- Function registry for that category
"""

from tools.nutrition_tools import NUTRITION_TOOLS
from tools.tool_runner import execute_tool_call
from tools.websearch_tools import WEBSEARCH_TOOLS

ALL_TOOLS = [*NUTRITION_TOOLS, *WEBSEARCH_TOOLS]

__all__ = [
    "ALL_TOOLS",
    "NUTRITION_TOOLS",
    "WEBSEARCH_TOOLS",
    "execute_tool_call",
]
