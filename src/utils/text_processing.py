import ftfy
from cleantext import clean


def clean_text_content(text: str) -> str:
    """
    Normalizes text for RAG.
    CRITICAL: Do NOT remove numbers (digits), as they represent floors,
    prices, rooms, and years in real estate.
    """
    if not text:
        return ""

    text = ftfy.fix_text(text)

    # Normalize
    text = clean(
        text,
        fix_unicode=True,
        to_ascii=False,
        lower=True,
        no_line_breaks=True,
        no_urls=True,
        no_emails=True,
        no_phone_numbers=False,
        no_emoji=True,
        no_digits=False,
    )
    return text
