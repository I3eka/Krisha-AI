import httpx
import asyncio
from typing import List, Dict, Any
from tenacity import retry, stop_after_attempt, wait_fixed
from src.config.settings import settings
from src.models import SearchQuery, InfrastructureFilter
from src.services.scraper import DataExtractor
from src.config.cache import cache


class KrishaClient:
    def __init__(self):
        self.semaphore = asyncio.Semaphore(20)
        self.client = httpx.AsyncClient(http2=True, timeout=30.0)

    def _build_search_params(self, query: SearchQuery) -> dict:
        params = {
            "appId": settings.KRISHA_APP_ID,
            "appKey": settings.KRISHA_APP_KEY,
            "catId": query.category_id,
            "limit": str(query.limit),
            "offset": str(query.offset),
            "query[data][map.geo_id][]": query.region_id,
            "orderBy[data][0][name]": "add_date",
            "orderBy[data][0][sort]": "desc",
        }

        if query.region_id == "1":
            params["query[data][map.geo_id][0]"] = "1"

        if query.price_to:
            params["query[data][_sys.price-2][to]"] = str(query.price_to)

        if query.price_from:
            params["query[data][_sys.price-2][from]"] = str(query.price_from)

        if query.room_count:
            for i, room in enumerate(query.room_count):
                params[f"query[data][live.rooms][or][{i}]"] = str(room)

        return params

    @cache(ttl="5m", key="listings:{query}")
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    async def fetch_listings(self, query: SearchQuery) -> List[dict]:
        url = f"{settings.BASE_URL}/v1/a/listing/search"
        params = self._build_search_params(query)

        resp = await self.client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        return [i["model"] for i in data.get("items", []) if i.get("kind") == "advert"]

    async def enrich_advert_data(
        self,
        advert_id: int,
        infra_filters: List[InfrastructureFilter],
        infra_operator: str = "AND",
    ) -> Dict[str, Any]:
        """
        Enrich advert with description and infrastructure data.

        Args:
            advert_id: The advert ID to enrich
            infra_filters: List of InfrastructureFilter objects
            infra_operator: "AND" or "OR" logic for filters
        """
        async with self.semaphore:
            show_task = self._fetch_raw_show(advert_id)
            infra_task = self._fetch_raw_infrastructure(advert_id)

            raw_show, raw_infra = await asyncio.gather(show_task, infra_task)

            return {
                "id": advert_id,
                "original_text": DataExtractor.parse_original_text(raw_show),
                "infrastructure": DataExtractor.parse_infrastructure(
                    raw_infra, filters=infra_filters, operator=infra_operator
                ),
            }

    @cache(ttl="1h")
    async def _fetch_raw_show(self, advert_id: int) -> Dict:
        url = f"{settings.BASE_URL}/v1/a/show"
        params = {
            "id": str(advert_id),
            "appId": settings.KRISHA_APP_ID,
            "appKey": settings.KRISHA_APP_KEY,
        }
        try:
            resp = await self.client.get(url, params=params)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return {}

    async def _fetch_raw_translation(self, advert_id: int) -> Dict:
        url = f"{settings.BASE_URL}/a/translate"
        params = {
            "id": str(advert_id),
            "appId": settings.KRISHA_APP_ID,
            "appKey": settings.KRISHA_APP_KEY,
        }
        try:
            resp = await self.client.get(url, params=params)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return {}

    @cache(ttl="1h")
    async def _fetch_raw_infrastructure(self, advert_id: int) -> Dict:
        url = f"{settings.BASE_URL}/infrastructure/getForAdvert"
        params = {
            "advertId": str(advert_id),
            "appId": settings.KRISHA_APP_ID,
            "appKey": settings.KRISHA_APP_KEY,
        }
        try:
            resp = await self.client.get(url, params=params)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return {}
