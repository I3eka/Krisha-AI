from pydantic import BaseModel, Field
from typing import List, Literal, Optional


class InfrastructureFilter(BaseModel):
    category: str = Field(
        ..., description="The API category key (e.g., 'metro', 'school')."
    )
    name_match: Optional[str] = Field(
        None,
        description="Strict substring to match in the place name. "
        "CRITICAL: Must be in **Russian Cyrillic** matching the API data. "
        "Example: User says 'Metro Abay' -> output 'Абай'. "
        "User says 'Metro Moscow' -> output 'Москва'. "
        "If generic (e.g. 'any school'), leave None.",
    )


class SearchQuery(BaseModel):
    """Structured output from LLM representing API parameters."""

    region_id: str = Field(
        ..., description="The ID of the city/region (e.g., '2' for Almaty)"
    )
    category_id: str = Field(..., description="Category ID (e.g., '2' for Rent Flat)")
    price_from: Optional[int] = None
    price_to: Optional[int] = None
    room_count: Optional[List[int]] = None
    limit: int = 256
    offset: int = 0
    semantic_query: str = Field(
        ...,
        description="The user request STRIPPED of city names, price numbers, room counts, generic property types (apartment, flat), AND infrastructure/landmarks handled by filters. "
        "The query must focus ONLY on descriptive adjectives, interior details, and 'vibes' (e.g., 'cozy', 'clean', 'euro renovation', 'panoramic view'). "
        "Do NOT include words like 'near Metro' or 'near School' here.",
    )
    constraints: List[str] = Field(
        default_factory=list,
        description="List of specific hard constraints extracted from user text. "
        "Examples: ['must_allow_students', 'must_allow_pets', 'must_have_separate_kitchen']",
    )
    infrastructure_filters: List[InfrastructureFilter] = Field(
        default_factory=list,
        description="List of strict filters. "
        "Example 1 (Generic): [{'category': 'school'}] -> Returns all schools. "
        "Example 2 (Strict): [{'category': 'metro', 'name_match': 'Москва'}] -> Returns ONLY 'Metro Moscow'. "
        "Example 3 (Multi): [{'category': 'grocery'}, {'category': 'pharmacy'}]",
    )
    infrastructure_operator: Literal["AND", "OR"] = Field(
        default="AND",
        description="Logical operator between infrastructure filters. "
        "'AND' = listing must match ALL filters (e.g., 'возле метро и рядом школа'). "
        "'OR' = listing must match AT LEAST ONE filter (e.g., 'либо возле метро, либо возле остановки').",
    )
