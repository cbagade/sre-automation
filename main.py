"""Main entry point for the SRE automation project.

This module demonstrates the nutrition assistant agent with example queries.
"""

from __future__ import annotations

import warnings

warnings.filterwarnings(
    "ignore",
    message="Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater.",
    category=UserWarning,
)

from agents import run_nutrition_assistant


def main() -> None:
    """Run example queries through the nutrition assistant."""

    # Example : Total Calorie lookup
    #user_query = "How many total calories are there in an apple and broccoli?"
    #user_query = "How many approx calories are there in Indian breakfast?"
    user_query = "Summarize Chandrakant Bagade's working at Persistent System's Ltd., profile from linked in"
    print(f"User: {user_query}\n")
    response = run_nutrition_assistant(user_query)
    print(f"Nutrition Assistant: {response}")    

    print("\n" + "=" * 50 + "\n")

    return None

    
    # Example : Calorie lookup
    user_query = "How many calories are in an apple?"
    print(f"User: {user_query}\n")
    response = run_nutrition_assistant(user_query)
    print(f"Nutrition Assistant: {response}")

    print("\n" + "=" * 50 + "\n")

    return None

    # Example : General nutrition question
    user_query2 = "What are the health benefits of bananas?"
    print(f"User: {user_query2}\n")
    response2 = run_nutrition_assistant(user_query2)
    print(f"Nutrition Assistant: {response2}")

    print("\n" + "=" * 50 + "\n")




if __name__ == "__main__":
    main()

# Made with Bob
