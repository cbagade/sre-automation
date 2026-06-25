"""Tool execution logic for handling OpenAI function calls.

This module provides utilities for executing tool calls from the OpenAI API,
including error handling and result formatting. Uses a dynamic registry pattern
to automatically discover and register tools from all tool category modules.
Includes Langfuse tracing for observability.
"""

import json
from typing import Callable
from utils.tracing import conditional_observe


# Global tool registry - tool categories auto-register on import
_TOOL_REGISTRY: dict[str, Callable[..., str]] = {}


def register_tool_category(functions: dict[str, Callable[..., str]]) -> None:
    """Register a tool category's functions in the global registry.
    
    This function is called by tool category modules to automatically
    register their functions when imported.
    
    Args:
        functions: Dictionary mapping function names to their implementations
    """
    _TOOL_REGISTRY.update(functions)


@conditional_observe(
    name="execute_tool_call",
    as_type="tool",
    capture_input=True,   # Capture tool call details for visibility
    capture_output=True   # Capture tool results for visibility
)
def execute_tool_call(tool_call) -> tuple[str, str]:
    """Execute a single tool call and return the result.
    
    Traced as a Langfuse tool observation. Captures tool execution
    details for debugging and observability.
    
    Args:
        tool_call: The tool call object from the model response containing:
            - name: The function name to call
            - call_id: Unique identifier for this call
            - arguments: JSON string of function arguments
        
    Returns:
        Tuple of (call_id, result_string) where:
            - call_id: The unique identifier for this tool call
            - result_string: The result from the function or error message
    
    Examples:
        >>> tool_call = ToolCall(name="get_food_calories", call_id="123", arguments='{"food_item": "apple"}')
        >>> call_id, result = execute_tool_call(tool_call)
        >>> print(result)
        'Apple: 80 calories per medium apple (182g)'
    """
    function_name = tool_call.name
    call_id = tool_call.call_id
    
    # Parse JSON arguments
    try:
        function_args = json.loads(tool_call.arguments)
    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON arguments received for tool {function_name}: {str(e)}"
        return call_id, error_msg
    
    # Look up the function in the global registry
    function_to_call = _TOOL_REGISTRY.get(function_name)
    
    if function_to_call is None:
        available_tools = ", ".join(_TOOL_REGISTRY.keys()) if _TOOL_REGISTRY else "none"
        error_msg = f"Unknown tool requested: {function_name}. Available tools: {available_tools}"
        return call_id, error_msg
    
    # Execute the function
    try:
        tool_result = function_to_call(**function_args)
    except TypeError as e:
        tool_result = f"Invalid arguments for {function_name}: {str(e)}"
    except Exception as e:
        tool_result = f"Error while running {function_name}: {str(e)}"
    
    return call_id, tool_result

# Made with Bob
