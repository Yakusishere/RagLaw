import re


def normalize_query(query: str) -> str:
    normalized = query.strip()
    normalized = re.sub(r"[ \u3000]+", " ", normalized)
    normalized = re.sub(r"[\t\r\n]+", " ", normalized)
    return normalized
