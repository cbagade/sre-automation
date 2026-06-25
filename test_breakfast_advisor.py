"""Test script for the breakfast advisor agent.

This script demonstrates the breakfast advisor agent orchestrating multiple agents
to provide comprehensive breakfast recommendations with calories and prices.
"""

from __future__ import annotations

import warnings

warnings.filterwarnings(
    "ignore",
    message="Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater.",
    category=UserWarning,
)

from agents import run_breakfast_advisor


def main() -> None:
    """Test the breakfast advisor agent with example queries."""

    print("=" * 80)
    print("BREAKFAST ADVISOR AGENT TEST")
    print("=" * 80)
    print()

    # Example 1: High-protein breakfast request
    user_query = "I need quick high-protein Indian breakfast ideas for busy mornings. Just 1 good idea will do. Please don't give me more than 1 ideas."
    print(f"User: {user_query}\n")
    print("Processing... (This may take a moment as multiple agents are orchestrated)\n")
    
    try:
        response = run_breakfast_advisor(user_query)
        print(f"Breakfast Advisor:\n{response}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()

# Made with Bob