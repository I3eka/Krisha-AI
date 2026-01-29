import asyncio
from loguru import logger
from price_parser import Price
from src.utils.logger import setup_logger
from src.services.llm_service import QueryParser
from src.services.api_client import KrishaClient
from src.services.vector_store import VectorEngine
from src.services.reranker import JinaReranker
from src.models import Advert
from src.config.cache import cache


async def main():
    setup_logger()
    cache.setup("mem://")
    logger.info("Cache initialized (In-Memory)")
    user_input = input("Enter your apartment search request: ")
    logger.info("Parsing query...")
    parser = QueryParser()
    params = await parser.parse_user_prompt(user_input)
    logger.info(
        f"Infrastructure Filters ({params.infrastructure_operator}): {params.infrastructure_filters}"
    )
    logger.info(f"Semantic Query (Decoupled): {params.semantic_query}")
    client = KrishaClient()
    logger.info("Fetching listings...")
    raw_listings = await client.fetch_listings(params)
    if not raw_listings:
        return print("No listings found.")
    logger.info(f"Enriching {len(raw_listings)} items...")
    enrich_tasks = [
        client.enrich_advert_data(
            i["id"], params.infrastructure_filters, params.infrastructure_operator
        )
        for i in raw_listings
    ]
    enriched_map = {d["id"]: d for d in await asyncio.gather(*enrich_tasks)}
    adverts = []
    dropped_count = 0
    for item in raw_listings:
        extra = enriched_map.get(item["id"], {})
        desc = extra.get("original_text", "")
        infra = extra.get("infrastructure", "")
        if params.infrastructure_filters and not infra:
            dropped_count += 1
            continue
        title = item.get("title", "")
        address = item.get("geoLocation", {}).get("addressTitle", "")
        full_text = f"Description: {desc}\nTitle: {title}"
        price_val = str(item.get("price") or item.get("priceTitle", "0"))
        clean_price = int(Price.fromstring(price_val).amount or 0)
        adverts.append(
            Advert(
                id=item["id"],
                title=title,
                price=clean_price,
                address=address,
                description=desc,
                url=f"https://krisha.kz/a/show/{item['id']}",
                full_text_content=full_text,
            )
        )
    logger.info(
        f"Kept {len(adverts)} items (Dropped {dropped_count} mismatching hard filters)"
    )
    logger.info("Vectorizing...")
    engine = VectorEngine()
    engine.index_data(adverts)
    candidates = engine.search(params.semantic_query, top_k=50)
    logger.info("Reranking with Jina...")
    results = await JinaReranker().rerank(user_input, candidates, top_k=20)
    print(f"\nTop {len(results)} Results:\n")
    for i, ad in enumerate(results, 1):
        print(f"{i}. {ad.title} - {ad.price:,} KZT".replace(",", " "))
        print(f"   Score: {ad.rag_score:.4f} | Address: {ad.address}")
        print(f"   Link: {ad.url}\n" + "-" * 40)


if __name__ == "__main__":
    asyncio.run(main())
