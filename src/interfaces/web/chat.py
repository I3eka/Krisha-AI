import chainlit as cl
from price_parser import Price
import asyncio
from src.config.cache import cache
from src.utils.logger import setup_logger
from src.services.llm_service import QueryParser
from src.services.api_client import KrishaClient
from src.services.vector_store import VectorEngine
from src.services.reranker import JinaReranker
from src.models import Advert, SearchQuery


@cl.set_starters
async def set_starters():
    return [
        cl.Starter(
            label="Almaty 2-Room",
            message="2 bedroom apartment in Almaty, Medeu district, near a park, max 400k",
            icon="/public/map.svg",
        ),
        cl.Starter(
            label="Cheap Student Flat",
            message="Cheap 1 room apartment in Almaty near KazNU university, allow students",
            icon="/public/student.svg",
        ),
        cl.Starter(
            label="Luxury House",
            message="Luxury house in Astana with a garage and sauna, budget unlimited",
            icon="/public/house.svg",
        ),
        cl.Starter(
            label="Pet Friendly",
            message="2 bedroom flat in Almaty, Bostandyk district, must allow cats",
            icon="/public/cat.svg",
        ),
    ]


@cl.on_chat_start
async def start():
    setup_logger()
    try:
        cache.setup("mem://")
    except Exception:
        pass


@cl.on_message
async def main(message: cl.Message):
    user_input = message.content
    async with cl.Step(name="Parsing", type="llm") as step:
        parser = QueryParser()
        params = await parser.parse_user_prompt(user_input)
        payload_details = [
            f"Region: {params.region_id}",
            f"Category: {params.category_id}",
        ]
        if params.room_count:
            payload_details.append(f"Rooms: {params.room_count}")
        if params.price_from:
            payload_details.append(f"Min Price: {params.price_from}")
        if params.price_to:
            payload_details.append(f"Max Price: {params.price_to}")
        payload_str = " | ".join(payload_details)
        infra_log = ""
        if params.infrastructure_filters:
            formatted_filters = [
                f"{f.category}: {f.name_match if f.name_match else 'Any'}"
                for f in params.infrastructure_filters
            ]
            infra_log = f"\n🔎 Infra Hard Filters ({params.infrastructure_operator}): {', '.join(formatted_filters)}"

        step.output = f"⚙️ API Payload: [{payload_str}]\n🧠 Semantic Query: '{params.semantic_query}'{infra_log}"
    cl.user_session.set("search_params", params)
    cl.user_session.set("user_query", user_input)
    await process_search_workflow(params, user_input)


async def process_search_workflow(params: SearchQuery, user_input: str):
    """
    Reusable workflow for fetching, enriching, vectorizing, and reranking.
    Used by both the initial search and the 'Load More' pagination.
    """
    results = []
    raw_listings_count = 0
    step_name = f"Search Batch (Offset: {params.offset})"
    async with cl.Step(name=step_name, type="run") as root_step:
        async with cl.Step(name="Fetching", type="tool") as step:
            client = KrishaClient()
            raw_listings = await client.fetch_listings(params)
            raw_listings_count = len(raw_listings)
            if not raw_listings:
                step.output = "❌ No listings found in this batch."
                await cl.Message(
                    content=f"No results found for offset {params.offset}."
                ).send()
                return
            step.output = f"Found {raw_listings_count} items (Offset: {params.offset})."
        async with cl.Step(name="Enriching", type="tool") as step:
            enrich_tasks = [
                client.enrich_advert_data(
                    i["id"],
                    params.infrastructure_filters,
                    params.infrastructure_operator,
                )
                for i in raw_listings
            ]
            enriched_results = await asyncio.gather(*enrich_tasks)
            enriched_map = {d["id"]: d for d in enriched_results}
            adverts = []
            dropped_count = 0
            for item in raw_listings:
                extra = enriched_map.get(item["id"], {})
                desc = extra.get("original_text", "")
                infra = extra.get("infrastructure", "")
                if params.infrastructure_filters and not infra:
                    dropped_count += 1
                    continue
                full_text = f"Description: {desc}\nTitle: {item.get('title')} Geolocation: {item.get('geoLocation', {}).get('district', '')} {item.get('geoLocation', {}).get('addressTitle', '')}"
                price_val = str(item.get("price") or item.get("priceTitle", "0"))
                clean_price = int(Price.fromstring(price_val).amount or 0)
                adverts.append(
                    Advert(
                        id=item["id"],
                        title=item.get("title", ""),
                        price=clean_price,
                        address=item.get("geoLocation", {}).get("addressTitle", ""),
                        description=desc,
                        url=f"https://krisha.kz/a/show/{item['id']}",
                        full_text_content=full_text,
                    )
                )
            step.output = f"Enriched {len(adverts)} items. (Dropped {dropped_count} by Hard Filter)"
        if adverts:
            async with cl.Step(name="Retrieval", type="retrieval") as step:
                engine = VectorEngine()
                engine.index_data(adverts)
                candidates = engine.search(params.semantic_query, top_k=50)
                step.output = (
                    f"Retrieved {len(candidates)} candidates via Semantic Search."
                )
            if candidates:
                async with cl.Step(name="Reranking", type="llm") as step:
                    reranker = JinaReranker()
                    results = await reranker.rerank(user_input, candidates, top_k=10)
                    step.output = f"Top {len(results)} selected."
        else:
            root_step.output = "No items in this batch matched the hard filters."

        root_step.output = f"✅ Processed {len(results)} results"
    if not results:
        await cl.Message("No relevant matches found in this batch.").send()
    else:
        for ad in results:
            price_fmt = f"{ad.price:,}".replace(",", " ")
            msg_content = f"""
### [{ad.title}]({ad.url})
**{price_fmt} ₸**  |  📍 {ad.address}  |  ⭐ {ad.rag_score:.2f}
{ad.description[:200]}...
"""
            await cl.Message(content=msg_content).send()
    if raw_listings_count > 0:
        actions = [
            cl.Action(
                name="load_more",
                value="next_page",
                label="Load Next 256 Listings",
                payload={"offset": params.offset},
            )
        ]
        prompt_text = (
            "Check the next batch?"
            if not results
            else "Not what you're looking for? Check the next batch."
        )
        await cl.Message(content=prompt_text, actions=actions).send()


@cl.action_callback("load_more")
async def on_load_more(action: cl.Action):
    await action.remove()
    params = cl.user_session.get("search_params")
    user_query = cl.user_session.get("user_query")
    if not params or not user_query:
        await cl.Message("Session expired. Please start a new search.").send()
        return
    params.offset += params.limit
    cl.user_session.set("search_params", params)
    await cl.Message(
        content=f"🔄 Loading listings {params.offset} - {params.offset + params.limit}..."
    ).send()
    await process_search_workflow(params, user_query)
