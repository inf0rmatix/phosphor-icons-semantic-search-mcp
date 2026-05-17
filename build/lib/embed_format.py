"""Shared text framing for index passages vs search queries (build + runtime)."""

PASSAGE_PREFIX = "passage:"
QUERY_PREFIX = "query:"


def format_passage_text(body: str) -> str:
    trimmed = body.strip()
    return f"{PASSAGE_PREFIX} {trimmed}" if trimmed else PASSAGE_PREFIX


def format_query_text(query: str) -> str:
    trimmed = query.strip()
    return f"{QUERY_PREFIX} {trimmed}" if trimmed else QUERY_PREFIX
