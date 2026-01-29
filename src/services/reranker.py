import instructor
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List
from src.models import Advert
from src.config.settings import settings
import httpx
from loguru import logger


class RankedAdvert(BaseModel):
    id: int
    location_score: int = Field(
        ..., description="0-10. How well does the location match? 10 is perfect."
    )
    quality_score: int = Field(
        ...,
        description="0-10. Does the description match the user's desired 'vibe' (renovation, clean, cozy, furniture)? "
        "If user didn't specify quality, give 10.",
    )
    constraints_score: int = Field(
        ...,
        description="0 or 1. 1 if ALL constraints (students, pets) are met. 0 if explicitly forbidden.",
    )
    reasoning: str = Field(..., description="Short explanation.")


class RankingResponse(BaseModel):
    ranked_items: List[RankedAdvert]


class LLMReranker:
    def __init__(self):
        self.client = instructor.from_openai(OpenAI())

    def rerank(
        self, query: str, constraints: List[str], adverts: List[Advert]
    ) -> List[Advert]:
        if not adverts:
            return []

        candidates_text = ""
        for ad in adverts:
            short_desc = (
                (ad.description[:400] + "..")
                if len(ad.description) > 400
                else ad.description
            )
            candidates_text += (
                f"ID: {ad.id} | Addr: {ad.address} | Desc: {short_desc}\n---\n"
            )

        system_prompt = f"""
        You are a Real Estate Scoring Engine.

        User Query: "{query}"
        Hard Constraints: {constraints}

        Evaluate each listing on 3 criteria:

        1. **Location Score (0-10)**: Proximity to requested landmarks.
        2. **Quality Score (0-10)**: Matches the requested condition (renovation, furniture, view, cozy, etc).
        3. **Constraints Score (0 or 1)**:
           - 0 = Explicitly forbids a requirement (e.g. "No students").
           - 1 = Allows it OR is silent/neutral.
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                response_model=RankingResponse,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": candidates_text},
                ],
            )

            ad_map = {ad.id: ad for ad in adverts}
            final_results = []

            for item in response.ranked_items:
                if item.id not in ad_map:
                    continue

                weighted_score = (item.location_score * 0.6) + (
                    item.quality_score * 0.4
                )
                final_score = weighted_score * item.constraints_score

                if final_score > 2.0:
                    ad_obj = ad_map[item.id]
                    ad_obj.rag_score = float(final_score)
                    final_results.append(ad_obj)

            final_results.sort(key=lambda x: x.rag_score, reverse=True)
            return final_results

        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return adverts


class JinaReranker:
    def __init__(self):
        self.api_url = "https://api.jina.ai/v1/rerank"
        self.headers = {
            "Authorization": f"Bearer {settings.JINA_API_KEY}",
            "Content-Type": "application/json",
        }

    async def rerank(
        self,
        query: str,
        adverts: List[Advert],
        top_k: int = 20,
        threshold: float = 0.3,
    ) -> List[Advert]:
        """
        Uses Jina AI to rerank documents.
        Applies a Relevance Threshold to filter out noise.
        """
        if not adverts:
            return []

        documents = [ad.full_text_content for ad in adverts]
        payload = {
            "model": "jina-reranker-v2-base-multilingual",
            "query": query,
            "documents": documents,
            "top_n": top_k,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url, headers=self.headers, json=payload
                )
                response.raise_for_status()
                results = response.json().get("results", [])

            reranked_adverts = []
            for item in results:
                score = item["relevance_score"]
                if score < threshold:
                    continue

                index = item["index"]
                ad = adverts[index]
                ad.rag_score = score
                reranked_adverts.append(ad)

            return reranked_adverts

        except Exception as e:
            logger.error(f"Jina Reranking failed: {e}")
            return adverts[:top_k]
