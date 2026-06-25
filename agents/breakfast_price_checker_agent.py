"""Breakfast price checker agent using OpenAI's API with web search tool.

This module provides an assistant that takes breakfast items with ingredients
and calories, then uses web search to find approximate prices for the ingredients.
Includes Langfuse tracing for observability with privacy controls.
"""

import os
from openai import OpenAI
from openai.types.responses import ResponseInputParam, Response
from dotenv import load_dotenv

import config
from tools.websearch_tools import WEBSEARCH_TOOLS, WEBSEARCH_FUNCTIONS
from tools.tool_runner import execute_tool_call
from utils.tracing import conditional_observe

# Agent instructions
PRICE_CHECKER_INSTRUCTIONS = """
You are a helpful assistant that takes multiple breakfast items (with ingredients and calories) and checks for the price of the ingredients.

Your responsibilities:
- Use the websearch_tool to get an approximate price for the ingredients.
- In your final output provide the meal name, ingredients with calories and price for each meal.
- Use markdown and be as concise as possible.

Guidelines:
- Search for current market prices of ingredients.
- Provide realistic price estimates based on web search results.
- Format output clearly using markdown tables or lists.
- Include both individual ingredient prices and total meal cost when possible.
- Be practical about portion sizes and quantities.
- If exact prices aren't available, provide reasonable estimates based on similar items.
"""

# Maximum number of tool execution iterations to prevent infinite loops
MAX_ITERATIONS = 10

# Initialize Langfuse tracing for OpenAI if enabled
if config.LANGFUSE_ENABLED:
    try:
        from langfuse.openai import register_tracing
        register_tracing()
    except ImportError:
        pass


def get_openai_client() -> OpenAI:
    """Get OpenAI client with API key from environment.
    
    When Langfuse is enabled, OpenAI calls are automatically traced as
    generations with model, tokens, cost, and latency captured via
    the register_tracing() initialization.
    
    Returns:
        Configured OpenAI client
        
    Raises:
        RuntimeError: If OPENAI_API_KEY is not set
    """
    load_dotenv()
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable not set.")
    
    return OpenAI(api_key=api_key)


def _create_response(input_items: ResponseInputParam) -> Response:
    """Create a response from the OpenAI API with consistent parameters.
    
    When Langfuse is enabled via register_tracing(), OpenAI calls are automatically
    traced as generation observations with model, tokens, cost, and latency.
    No decorator needed as register_tracing() handles instrumentation.
    
    Args:
        input_items: The conversation history and tool results
        
    Returns:
        Response object from the OpenAI API
    """
    client = get_openai_client()
    
    response = client.responses.create(
        model=config.OPENAI_DEFAULT_MODEL,
        instructions=PRICE_CHECKER_INSTRUCTIONS,
        input=input_items,
        tools=WEBSEARCH_TOOLS,
        temperature=0.7,
    )
    
    return response


@conditional_observe(
    name="breakfast_price_checker",
    capture_input=True,   # Capture user messages for full visibility
    capture_output=True   # Capture assistant responses for full visibility
)
def run_breakfast_price_checker(user_message: str) -> str:
    """Run the breakfast price checker assistant with web search tool support.
    
    This function handles the complete conversation loop, including:
    - Sending the user message with breakfast items to the model
    - Executing web search tool calls to find ingredient prices
    - Returning tool results back to the model
    - Iterating until a final formatted response is generated
    
    Full tracing enabled: Captures all inputs and outputs for complete observability.
    
    Args:
        user_message: The user's breakfast items with ingredients and calories
        
    Returns:
        The assistant's response with meal names, ingredients, calories, and prices
        formatted in markdown
        
    Raises:
        RuntimeError: If maximum iterations are exceeded, indicating
            the model may be stuck in a tool-calling loop
    
    Examples:
        >>> breakfast_items = '''
        ... 1. Greek Yogurt Parfait - Greek yogurt (200g), granola (50g), berries (100g) - 350 calories
        ... 2. Avocado Toast - Whole wheat bread (2 slices), avocado (1/2), eggs (2) - 400 calories
        ... '''
        >>> response = run_breakfast_price_checker(breakfast_items)
        >>> print(response)
        '## Breakfast Price Breakdown
        
        ### 1. Greek Yogurt Parfait (350 calories)
        - Greek yogurt (200g): $1.50
        - Granola (50g): $0.75
        - Berries (100g): $2.00
        **Total: $4.25**
        ...'
    """
    print(f"\n[BREAKFAST PRICE CHECKER AGENT] Received meal plan to price")
    input_items: ResponseInputParam = [
        {
            "role": "user",
            "content": user_message
        }
    ]

    response = _create_response(input_items)
    
    # Keep looping in case the model calls one or more tools
    iteration_count = 0
    tool_calls_made = []
    
    while iteration_count < MAX_ITERATIONS:
        iteration_count += 1
        
        # Extract function calls from response
        function_calls = [
            item for item in response.output
            if item.type == "function_call"
        ]

        # If no function calls, return the text response
        if not function_calls:
            final_response = response.output_text or ""
            return final_response

        # Add the entire response output to maintain conversation context
        input_items.extend(response.output)  # type: ignore[arg-type]
        
        # Execute all tool calls and collect results
        for tool_call in function_calls:
            tool_calls_made.append(tool_call.name)
            
            # Execute the tool call using the generic tool runner
            call_id, tool_result = execute_tool_call(tool_call)
            
            input_items.append({
                "type": "function_call_output",
                "call_id": call_id,
                "output": tool_result
            })

        # Send tool results back to the model
        response = _create_response(input_items)
    
    # If we've exceeded max iterations, raise an error
    error_msg = (
        f"Maximum iterations ({MAX_ITERATIONS}) exceeded. "
        "The model may be stuck in a tool-calling loop."
    )
    
    raise RuntimeError(error_msg)


# Made with Bob