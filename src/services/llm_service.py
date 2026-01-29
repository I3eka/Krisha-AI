import instructor
from openai import AsyncOpenAI
from src.models import SearchQuery
from src.utils.mappings import REGION_MAP, CATEGORY_MAP
from src.config.cache import cache


class QueryParser:
    def __init__(self):
        self.client = instructor.from_openai(AsyncOpenAI())

    @cache(ttl="24h")
    async def parse_user_prompt(self, user_text: str) -> SearchQuery:
        system_prompt = f"""
        You are a search engine for Krisha.kz.
        Your goal is to map the user's request to API parameters AND create a clean semantic search string.

        Reference Data:
        - Region IDs: {REGION_MAP}
        - Category IDs: {CATEGORY_MAP}

        Rules for 'category_id':
        1. DEFAULT: If user does NOT explicitly mention buying or renting, use "Rent Apartment (Monthly)" (ID: "2").
        2. Keywords for BUYING (use "Buy Apartment" or "Buy House/Dacha"):
           - Russian: "купить", "покупка", "приобрести", "в собственность"
           - English: "buy", "purchase"
           - Kazakh: "сатып алу"
        3. Keywords for RENTING (use "Rent Apartment (Monthly)" or other rent categories):
           - Russian: "снять", "аренда", "арендовать", "в аренду"
           - English: "rent", "lease"
           - Kazakh: "жалға алу"
        4. If user mentions "дом" or "дача" (house/dacha), use House/Dacha categories accordingly.
        5. For daily/hourly rent, look for keywords like "посуточно", "на день", "почасово", "на час".
        6. IMPORTANT: Generic words like "найти", "ищу", "нужна" (find, looking for, need) do NOT indicate buying - default to rent.

        Rules for 'room_count':
        - Extract specific room counts into the list. "однушку" -> [1].

        Rules for 'infrastructure_filters':
        1. Identify intent: Does user need a specific station/place?
        2. Categories: ['metro', 'bus', 'school', 'kindergarten', 'grocery', 'supermarket', 'mall', 'pharmacy', 'gym', 'park'].
        3. TRANSLATION REQUIRED: The database names are in Russian.
           - User: "Metro Abay" -> {{ "category": "metro", "name_match": "Абай" }}
           - User: "Near Magnum" -> {{ "category": "supermarket", "name_match": "Magnum" }}
           - User: "Metro Moscow" -> {{ "category": "metro", "name_match": "Москва" }}
           - User: "near bus stop" -> {{ "category": "bus", "name_match": null }}

        Rules for 'infrastructure_operator':
        1. Default is 'AND' (all infrastructure conditions must be met).
        2. Use 'OR' when user explicitly uses words like:
           - Russian: "либо...либо", "или", "один из"
           - English: "any of", "either...or", "or"
           - Example: "либо возле метро, либо возле остановки" -> "OR"
           - Example: "either near metro or near bus stop" -> "OR"
        3. Use 'AND' when user uses words like:
           - Russian: "и", "а также", "плюс", "рядом с ... и ..."
           - English: "both", "and", "as well as"
           - Example: "возле метро и рядом школа" -> "AND"
           - Example: "near metro and near school" -> "AND"

        Rules for 'semantic_query':
        1. Formulate a search string that describes the property features and vibe.
        2. CRITICAL: STRIP out any locations, landmarks, or infrastructure that you extracted into 'infrastructure_filters'.
           - If user says "Cozy flat near Metro Moscow", the semantic query should be "Cozy flat". (Metro Moscow is a hard filter).
        3. The database contains ads in Russian, English, and Kazakh.
           To ensure maximum recall, your semantic_query MUST follow this format:
           "[Original keywords in User Language] [English Translation of keywords]"
        4. EXAMPLE:
           Input: "Мысықпен тұруға болатын пәтер"
           Output: "Мысықпен тұруға болатын пәтер. Apartment allowing cats pets."
        5. Exclude city names, prices, and room counts.

        Rules for 'constraints':
        - Extract specific requirements (e.g. ["allow_students", "allow_pets"]).
        """

        return await self.client.chat.completions.create(
            model="gpt-4o-mini",
            response_model=SearchQuery,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
        )
