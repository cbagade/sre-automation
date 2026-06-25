"""Nutrition-specific tools for calorie and dietary information.

This module contains local nutrition lookup tools backed by the project's
ChromaDB dataset. It is intentionally focused on local nutrition retrieval,
while remote web search functionality lives in a separate module.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Callable

import chromadb
from openai.types.responses import ToolParam

from tools.tool_runner import register_tool_category
from utils.tracing import conditional_observe

chroma_client = chromadb.PersistentClient("data/chroma")
nutrition_db = chroma_client.get_collection(name="nutrition_db")

NO_RESULTS_PREFIX = "No nutrition information found"
WEAK_MATCH_PREFIX = "Weak nutrition match"
AMBIGUOUS_MATCH_PREFIX = "Ambiguous nutrition match"


def _normalize_food_name(food_item: str) -> str:
    """Normalize a food item string for comparison."""
    return " ".join(food_item.lower().strip().split())


def _is_strong_food_match(query: str, candidate: str) -> bool:
    """Determine whether a retrieved food item strongly matches the query."""
    normalized_query = _normalize_food_name(query)
    normalized_candidate = _normalize_food_name(candidate)

    if normalized_query == normalized_candidate:
        return True

    query_tokens = set(normalized_query.split())
    candidate_tokens = set(normalized_candidate.split())

    if not query_tokens or not candidate_tokens:
        return False

    overlap_ratio = len(query_tokens & candidate_tokens) / len(query_tokens)
    return overlap_ratio >= 0.8


def _format_nutrition_result(food_name: str, category: str, calories: Any) -> str:
    """Format a single nutrition lookup result line."""
    return f"{food_name} ({category}): {calories} calories per 100g"


def _classify_lookup_results(
    food_item: str,
    metadatas: Sequence[Mapping[str, Any]],
) -> tuple[str, list[str]]:
    """Classify lookup quality and format nutrition results.

    Args:
        food_item: Original user query.
        metadatas: Metadata rows returned from ChromaDB.

    Returns:
        Tuple of (quality_label, formatted_results).
    """
    formatted_results: list[str] = []
    strong_matches = 0

    for metadata in metadatas:
        food_name = str(metadata.get("food_item", "Unknown")).title()
        calories = metadata.get("calories_per_100g", 0)
        category = str(metadata.get("food_category", "Unknown")).title()

        formatted_results.append(
            _format_nutrition_result(
                food_name=food_name,
                category=category,
                calories=calories,
            )
        )

        if _is_strong_food_match(food_item, food_name):
            strong_matches += 1

    if not formatted_results:
        return "none", []

    if strong_matches == 0:
        return "weak", formatted_results

    if strong_matches > 1:
        return "ambiguous", formatted_results

    return "strong", formatted_results


@conditional_observe(
    name="get_food_calories",
    as_type="tool",
    capture_input=True,
    capture_output=True,
)
def calorie_lookup(food_item: str, max_results: int = 3) -> str:
    """Look up calorie information for a food item from the local nutrition DB.

    The response intentionally signals result quality so the model can decide
    when to fall back to web search.

    Args:
        food_item: The food item to look up.
        max_results: Maximum number of local matches to return.

    Returns:
        A formatted string containing nutrition information and match quality.
    """
    print(
        f"\n[TOOL: get_food_calories] Looking up calories for '{food_item}'...",
        flush=True,
    )
    results = nutrition_db.query(query_texts=[food_item], n_results=max_results)

    if not results:
        return f"{NO_RESULTS_PREFIX}: {food_item}"

    documents_list = results.get("documents")
    if not documents_list or not documents_list[0]:
        return f"{NO_RESULTS_PREFIX}: {food_item}"

    metadatas_list = results.get("metadatas")
    metadatas = metadatas_list[0] if metadatas_list else []

    quality, formatted_results = _classify_lookup_results(food_item, metadatas)

    if not formatted_results:
        return f"{NO_RESULTS_PREFIX}: {food_item}"

    if quality == "weak":
        return (
            f"{WEAK_MATCH_PREFIX} for '{food_item}'. "
            "Use websearch_tool if you need more reliable or broader information.\n"
            + "\n".join(formatted_results)
        )

    if quality == "ambiguous":
        return (
            f"{AMBIGUOUS_MATCH_PREFIX} for '{food_item}'. "
            "Use websearch_tool if the user needs clarification or broader context.\n"
            + "\n".join(formatted_results)
        )

    return "Nutrition Information:\n" + "\n".join(formatted_results)


NUTRITION_TOOLS: list[ToolParam] = [
    {
        "type": "function",
        "name": "get_food_calories",
        "description": (
            "Look up calorie information for a specific food item from the local "
            "nutrition database. Use this first for direct calorie questions."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "food_item": {
                    "type": "string",
                    "description": (
                        "The name of the food item, e.g. apple, banana, broccoli."
                    ),
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of local matches to return.",
                    "minimum": 1,
                    "maximum": 10,
                    "default": 3,
                },
            },
            "required": ["food_item", "max_results"],
            "additionalProperties": False,
        },
    }
]


NUTRITION_FUNCTIONS: dict[str, Callable[..., str]] = {
    "get_food_calories": calorie_lookup,
}

register_tool_category(NUTRITION_FUNCTIONS)
