from ollama import chat
from typing import Literal
from pydantic import BaseModel, Field, model_validator

from ..models import Category


class ProductSearchFilters(BaseModel):
    search: str | None = Field(
        default=None,
        description="Product name, type, feature, or other text-search keywords only.",
    )
    category: str | None = Field(
        default=None,
        description="An exact category name from the supplied category list.",
    )
    min_price: float | None = Field(default=None, ge=0)
    max_price: float | None = Field(default=None, ge=0)

    ordering: Literal[
        "price",
        "-price",
        "name",
        "-name",
    ] | None = None

    @model_validator(mode="after")
    def validate_price_range(self):
        if (
            self.min_price is not None
            and self.max_price is not None
            and self.min_price > self.max_price
        ):
            raise ValueError("min_price cannot be greater than max_price")
        return self


def _build_system_prompt(categories: list[str]) -> str:
    category_list = ", ".join(categories) if categories else "(none)"
    return f"""You convert a shopping request into product search filters.
Return one JSON object matching the supplied schema. Return no explanation.

Available categories (case-sensitive): {category_list}

Extraction rules:
- Set every filter that the request does not specify to null.
- `search` contains only product names, product types, features, brands, or other
  useful catalog keywords. Keep it short. Do not include filler words, prices,
  currency names/symbols, category names, or sorting phrases in `search`.
- `category` must exactly match one available category, including its casing.
  Set it only if the user explicitly names that category. Never guess a broader
  category from a product type. If there are no available categories, it is null.
- Use `max_price` for "under", "below", "up to", "at most", or a stated budget.
- Use `min_price` for "over", "above", "at least", or "starting from".
- For "between X and Y", set `min_price` to X and `max_price` to Y.
- Store price amounts as numbers without currency symbols. Do not convert currencies.
- Set `ordering` only when sorting is explicitly requested: cheapest/lowest price
  is "price", most expensive/highest price is "-price", name A-Z is "name", and
  name Z-A is "-name".
- Never invent a filter.

Examples below assume the available categories are Electronics and Books:
User: I need a laptop under 900 dollars
Output: {{"search":"laptop","category":null,"min_price":null,"max_price":900,"ordering":null}}

User: Show me gaming mice between $25 and $80, cheapest first
Output: {{"search":"gaming mice","category":null,"min_price":25,"max_price":80,"ordering":"price"}}

User: Show me Electronics products
Output: {{"search":null,"category":"Electronics","min_price":null,"max_price":null,"ordering":null}}
"""

def extract_product_filters(message: str) -> ProductSearchFilters:
    categories = list(
        Category.objects
        .order_by("name")
        .values_list("name", flat=True)
    )

    response = chat(
        model="qwen3:4b",
        messages=[
            {
                "role": "system",
                "content": _build_system_prompt(categories),
            },
            {
                "role": "user",
                "content": message,
            },
        ],
        format=ProductSearchFilters.model_json_schema(),
        options={"temperature": 0},
    )

    filters = ProductSearchFilters.model_validate_json(
        response.message.content
    )

    return filters
