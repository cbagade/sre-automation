"""Agents package for AI assistant implementations.

This package contains agent implementations that use OpenAI's API
with tool calling capabilities.
"""

from agents.nutrition_agent import run_nutrition_assistant
from agents.healthy_breakfast_planner_agent import run_breakfast_planner
from agents.breakfast_price_checker_agent import run_breakfast_price_checker
from agents.breakfast_advisor_agent import run_breakfast_advisor

__all__ = [
    "run_nutrition_assistant",
    "run_breakfast_planner",
    "run_breakfast_price_checker",
    "run_breakfast_advisor",
]

# Made with Bob
