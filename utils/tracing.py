"""Conditional tracing utilities for Langfuse integration.

This module provides conditional observe decorators that respect
the LANGFUSE_ENABLED configuration flag and implement privacy controls.
"""

from functools import wraps
from typing import Callable, Any, Optional, Literal
import config


ObservationType = Literal["generation", "span", "tool", "agent", "embedding"]


def conditional_observe(
    name: Optional[str] = None,
    as_type: Optional[ObservationType] = None,
    capture_input: bool = False,
    capture_output: bool = False,
    **kwargs
):
    """Conditional decorator for Langfuse tracing with privacy controls.
    
    Only applies @observe decorator if LANGFUSE_ENABLED is True.
    By default, does NOT capture inputs/outputs to protect sensitive data.
    
    Args:
        name: Name for the trace span
        as_type: Type of observation ("generation", "span", "tool", "agent", "embedding")
        capture_input: Whether to capture function inputs (default: False for privacy)
        capture_output: Whether to capture function outputs (default: False for privacy)
        **kwargs: Additional arguments for @observe decorator
        
    Returns:
        Decorator function
        
    Examples:
        >>> @conditional_observe(name="openai_call", as_type="generation", capture_input=False)
        >>> def call_openai():
        >>>     pass
    """
    def decorator(func: Callable) -> Callable:
        if config.LANGFUSE_ENABLED:
            # Import langfuse only if enabled
            from langfuse import observe
            return observe(
                name=name,
                as_type=as_type,
                capture_input=capture_input,
                capture_output=capture_output,
                **kwargs
            )(func)
        else:
            # Return function unchanged if tracing disabled
            return func
    
    return decorator

# Made with Bob
