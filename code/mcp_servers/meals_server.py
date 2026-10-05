from __future__ import annotations

import logging
import sys
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP


API_BASE = (
    "https://www.themealdb.com/"
    "api/json/v1/1"
)

REQUEST_TIMEOUT_SECONDS = 15.0

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format=(
        "%(asctime)s %(levelname)s "
        "%(name)s: %(message)s"
    )
)

logger = logging.getLogger(
    "meals_server"
)

mcp = FastMCP("meals")


def validate_text(
    value: str,
    field_name: str
) -> str:
    """Return cleaned nonempty text."""

    cleaned = str(value).strip()

    if not cleaned:
        raise ValueError(
            f"{field_name} must not be empty."
        )

    return cleaned


def validate_limit(
    limit: int,
    maximum: int = 25
) -> int:
    """Validate a requested result limit."""

    if not isinstance(limit, int):
        raise ValueError(
            "limit must be an integer."
        )

    if limit < 1 or limit > maximum:
        raise ValueError(
            f"limit must be between 1 and {maximum}."
        )

    return limit


async def request_mealdb(
    endpoint: str,
    params: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Call TheMealDB and return decoded JSON."""

    try:
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT_SECONDS
        ) as client:
            response = await client.get(
                f"{API_BASE}/{endpoint}",
                params=params
            )

            response.raise_for_status()
            payload = response.json()

    except httpx.TimeoutException as error:
        logger.error(
            "TheMealDB request timed out: %s",
            endpoint
        )

        raise RuntimeError(
            "TheMealDB request timed out."
        ) from error

    except httpx.HTTPStatusError as error:
        logger.error(
            "TheMealDB returned HTTP %s.",
            error.response.status_code
        )

        raise RuntimeError(
            "TheMealDB returned an HTTP error."
        ) from error

    except (
        httpx.RequestError,
        ValueError
    ) as error:
        logger.error(
            "TheMealDB request failed: %s",
            error
        )

        raise RuntimeError(
            "Unable to retrieve valid recipe data."
        ) from error

    if not isinstance(payload, dict):
        raise RuntimeError(
            "TheMealDB returned an unexpected response."
        )

    return payload


def compact_meal(
    meal: dict[str, Any]
) -> dict[str, Any]:
    """Return a compact name-search result."""

    return {
        "id": meal.get("idMeal"),
        "name": meal.get("strMeal"),
        "area": meal.get("strArea"),
        "category": meal.get("strCategory"),
        "thumb": meal.get("strMealThumb")
    }


def ingredient_meal(
    meal: dict[str, Any]
) -> dict[str, Any]:
    """Return a compact ingredient-search result."""

    return {
        "id": meal.get("idMeal"),
        "name": meal.get("strMeal"),
        "thumb": meal.get("strMealThumb")
    }


def full_meal(
    meal: dict[str, Any]
) -> dict[str, Any]:
    """Return complete recipe details."""

    ingredients: list[dict[str, str]] = []

    for number in range(1, 21):
        ingredient = str(
            meal.get(
                f"strIngredient{number}"
            )
            or ""
        ).strip()

        measure = str(
            meal.get(
                f"strMeasure{number}"
            )
            or ""
        ).strip()

        if ingredient:
            ingredients.append({
                "name": ingredient,
                "measure": measure
            })

    return {
        "id": meal.get("idMeal"),
        "name": meal.get("strMeal"),
        "category": meal.get("strCategory"),
        "area": meal.get("strArea"),
        "instructions": (
            meal.get("strInstructions")
        ),
        "image": meal.get("strMealThumb"),
        "source": meal.get("strSource"),
        "youtube": meal.get("strYoutube"),
        "ingredients": ingredients
    }


@mcp.tool()
async def search_meals_by_name(
    query: str,
    limit: int = 5
) -> list[dict[str, Any]]:
    """
    Search for meals by name.

    Returns an empty list when there are no matches.
    """

    cleaned_query = validate_text(
        query,
        "query"
    )

    checked_limit = validate_limit(
        limit
    )

    payload = await request_mealdb(
        "search.php",
        {
            "s": cleaned_query
        }
    )

    meals = payload.get("meals")

    if meals is None:
        logger.info(
            "No meal-name matches for %s.",
            cleaned_query
        )
        return []

    if not isinstance(meals, list):
        raise RuntimeError(
            "TheMealDB returned invalid meal results."
        )

    return [
        compact_meal(meal)
        for meal in meals[:checked_limit]
    ]


@mcp.tool()
async def meals_by_ingredient(
    ingredient: str,
    limit: int = 12
) -> list[dict[str, Any]]:
    """
    Find meals using one main ingredient.

    Returns an empty list when there are no matches.
    """

    cleaned_ingredient = validate_text(
        ingredient,
        "ingredient"
    )

    checked_limit = validate_limit(
        limit
    )

    payload = await request_mealdb(
        "filter.php",
        {
            "i": cleaned_ingredient
        }
    )

    meals = payload.get("meals")

    if meals is None:
        logger.info(
            "No ingredient matches for %s.",
            cleaned_ingredient
        )
        return []

    if not isinstance(meals, list):
        raise RuntimeError(
            "TheMealDB returned invalid meal results."
        )

    return [
        ingredient_meal(meal)
        for meal in meals[:checked_limit]
    ]


@mcp.tool()
async def meal_details(
    id: str | int
) -> dict[str, Any]:
    """Return full recipe details for one meal ID."""

    cleaned_id = validate_text(
        str(id),
        "id"
    )

    if not cleaned_id.isdigit():
        raise ValueError(
            "id must contain digits only."
        )

    payload = await request_mealdb(
        "lookup.php",
        {
            "i": cleaned_id
        }
    )

    meals = payload.get("meals")

    if not isinstance(meals, list) or not meals:
        return {
            "message": "no matches",
            "id": cleaned_id
        }

    return full_meal(
        meals[0]
    )


@mcp.tool()
async def random_meal() -> dict[str, Any]:
    """Return one random meal with full details."""

    payload = await request_mealdb(
        "random.php"
    )

    meals = payload.get("meals")

    if not isinstance(meals, list) or not meals:
        return {
            "message": "no matches"
        }

    return full_meal(
        meals[0]
    )


if __name__ == "__main__":
    logger.info(
        "Starting meals MCP server over STDIO."
    )

    mcp.run(    
        transport="stdio"
    )   