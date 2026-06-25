"""Healthy breakfast planner agent using OpenAI's API.

This module provides a helpful assistant that suggests healthy breakfast meals
for busy people based on their preferences. Uses base LLM without tool calling.
Includes Langfuse tracing for observability with privacy controls.
"""

import os
from openai import OpenAI
from openai.types.responses import ResponseInputParam, Response
from dotenv import load_dotenv

import config
from utils.tracing import conditional_observe

# Agent instructions
BREAKFAST_PLANNER_INSTRUCTIONS = """
You are a helpful assistant that helps with healthy breakfast choices.

Your responsibilities:
- You give concise answers.
- Given the user's preferences prompt, come up with different breakfast meals that are healthy and fit for a busy person.
- Explicitly mention the meal's names in your response along with a sentence of why this is a healthy choice.

Guidelines:
- Focus on quick, nutritious breakfast options suitable for busy lifestyles.
- Consider variety in your suggestions (protein-rich, fiber-rich, balanced meals).
- Keep explanations brief but informative.
- Mention preparation time if relevant.
- Be practical and realistic about what busy people can prepare.
"""

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
        input_items: The conversation history
        
    Returns:
        Response object from the OpenAI API
    """
    client = get_openai_client()
    
    response = client.responses.create(
        model=config.OPENAI_DEFAULT_MODEL,
        instructions=BREAKFAST_PLANNER_INSTRUCTIONS,
        input=input_items,
        temperature=0.7,
    )
    
    return response


@conditional_observe(
    name="breakfast_planner_assistant",
    capture_input=True,   # Capture user messages for full visibility
    capture_output=True   # Capture assistant responses for full visibility
)
def run_breakfast_planner(user_message: str) -> str:
    """Run the healthy breakfast planner assistant.
    
    This function handles the conversation with the model to generate
    healthy breakfast suggestions based on user preferences. No tool
    calling is involved - uses base LLM only.
    
    Full tracing enabled: Captures all inputs and outputs for complete observability.
    
    Args:
        user_message: The user's preferences or request for breakfast suggestions
        
    Returns:
        The assistant's response with breakfast meal suggestions
    
    Examples:
        >>> response = run_breakfast_planner("I need quick breakfast ideas with high protein")
        >>> print(response)
        'Here are some healthy breakfast options:
        1. Greek Yogurt Parfait - High in protein and probiotics...
        2. Scrambled Eggs with Whole Wheat Toast - Provides complete protein...'
    """
    print(f"\n[BREAKFAST PLANNER AGENT] Received query: {user_message}")
    input_items: ResponseInputParam = [
        {
            "role": "user",
            "content": user_message
        }
    ]

    response = _create_response(input_items)
    
    # Extract and return the text response
    final_response = response.output_text or ""
    return final_response


# Made with Bob