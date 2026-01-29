from pydantic import BaseModel
from typing import List


class Advert(BaseModel):
    """Normalized Advertisement Data."""

    id: int
    title: str
    price: int
    address: str
    description: str = ""
    url: str
    photos: List[str] = []
    full_text_content: str = ""
    rag_score: float = 0.0
