"""Nutrition assistant agent using OpenAI's API with tool calling.

This module provides a nutrition expert assistant that can answer questions
about food and nutrition, with the ability to look up calorie information
using available tools. Includes Langfuse tracing for observability with privacy controls.
"""

import os
from openai import OpenAI
from openai.types.responses import ResponseInputParam, Response
from dotenv import load_dotenv

import config
from tools import ALL_TOOLS, execute_tool_call
from utils.tracing import conditional_observe

# Agent instructions
NUTRITION_ASSISTANT_INSTRUCTIONS = """
You are a professional nutrition expert and dietitian assistant.

Your responsibilities:
- Give concise, accurate answers about nutrition and food.
- Use the get_food_calories tool first for direct calorie lookup questions about foods.
- Use the websearch_tool when:
  - get_food_calories returns no nutrition information found
  - get_food_calories returns a weak nutrition match
  - get_food_calories returns an ambiguous nutrition match
  - the user asks broader nutrition, diet, health-food, or food fact questions that require web context

Guidelines:
- Prefer local nutrition lookup before web search for direct calorie questions.
- If local results are weak or ambiguous, use websearch_tool to improve confidence.
- For general nutrition questions, you may use websearch_tool directly when local calorie lookup is not sufficient.
- When using web results, summarize clearly and avoid overstating certainty.
- Remind users to consult healthcare professionals for medical conditions.
- Use clear, easy-to-understand language.
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
        instructions=NUTRITION_ASSISTANT_INSTRUCTIONS,
        input=input_items,
        tools=ALL_TOOLS,
        temperature=0.7,
    )
    
    return response


@conditional_observe(
    name="nutrition_assistant",
    capture_input=True,   # Capture user messages for full visibility
    capture_output=True   # Capture assistant responses for full visibility
)
def run_nutrition_assistant(user_message: str) -> str:
    """Run the nutrition assistant with tool support.
    
    This function handles the complete conversation loop, including:
    - Sending the user message to the model
    - Executing any tool calls requested by the model
    - Returning tool results back to the model
    - Iterating until a final text response is generated
    
    Full tracing enabled: Captures all inputs and outputs for complete observability.
    
    Args:
        user_message: The user's question or request
        
    Returns:
        The assistant's response as a string
        
    Raises:
        RuntimeError: If maximum iterations are exceeded, indicating
            the model may be stuck in a tool-calling loop
    
    Examples:
        >>> response = run_nutrition_assistant("How many calories are in an apple?")
        >>> print(response)
        'An apple contains approximately 80 calories per medium apple (182g).'
    """
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
