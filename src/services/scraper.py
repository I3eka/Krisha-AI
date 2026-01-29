from typing import Dict, Any, List, Set, Optional, Tuple
from src.models import InfrastructureFilter


class DataExtractor:
    @staticmethod
    def parse_original_text(response_data: Dict[str, Any]) -> str:
        if not response_data:
            return ""
        return response_data.get("text", "").strip()

    @staticmethod
    def parse_infrastructure(
        response_data: Dict[str, Any],
        filters: List[InfrastructureFilter],
        operator: str = "AND",
    ) -> str:
        """
        Parses infrastructure using hash map for O(1) category lookup.
        Supports AND/OR logic between filters.

        Args:
            response_data: Raw API response from infrastructure endpoint
            filters: List of InfrastructureFilter objects
            operator: "AND" (all filters must match) or "OR" (at least one must match)

        Returns:
            Formatted string of matched infrastructure, or empty string if filters not satisfied
        """
        data = response_data.get("data", [])
        if not data or not filters:
            return ""

        filter_map: Dict[str, Set[Optional[str]]] = {}
        for f in filters:
            cat = f.category.lower()
            if cat not in filter_map:
                filter_map[cat] = set()
            filter_map[cat].add(f.name_match.lower() if f.name_match else None)

        matched_filters: Set[Tuple[str, Optional[str]]] = set()
        matched_places: List[Dict[str, Any]] = []

        required_filters: Set[Tuple[str, Optional[str]]] = {
            (f.category.lower(), f.name_match.lower() if f.name_match else None)
            for f in filters
        }

        for section in data:
            for place in section.get("places", []):
                p_cat = place.get("category", "").lower()
                p_name = place.get("name", "")

                if p_cat not in filter_map:
                    continue

                name_matches = filter_map[p_cat]

                for name_match in name_matches:
                    if name_match is None:
                        matched_filters.add((p_cat, None))
                        matched_places.append(place)
                        break
                    elif name_match in p_name.lower():
                        matched_filters.add((p_cat, name_match))
                        matched_places.append(place)
                        break

        if operator == "AND":
            if not required_filters.issubset(matched_filters):
                return ""
        else:
            if not matched_filters:
                return ""

        if not matched_places:
            return ""

        grouped: Dict[str, List[str]] = {}
        for place in matched_places:
            p_title = place.get("title", "Инфраструктура")
            p_name = place.get("name", "")
            dist = place.get("distance", "")

            place_str = f"{p_name} ({dist})" if dist else p_name

            if p_title not in grouped:
                grouped[p_title] = []
            if place_str not in grouped[p_title]:
                grouped[p_title].append(place_str)

        text_parts = []
        for title, places in grouped.items():
            joined = ", ".join(places)
            text_parts.append(f"{title}: {joined}")

        return ". ".join(text_parts)
