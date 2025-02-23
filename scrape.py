# /// script
# dependencies = ["msgspec", "loguru", "httpx"]
# ///
import calendar
from datetime import datetime
from itertools import product
import json
import re

import msgspec
from loguru import logger
import httpx


class Hit(msgspec.Struct):
    story_id: int
    author: str
    title: str | None = None
    text: str | None = None


class SearchResponse(msgspec.Struct):
    hits: list[Hit]


class ItemResponse(msgspec.Struct):
    children: list[Hit]


years = range(2007, datetime.today().year + 1)
months = list(calendar.month_name)[1:]
queries = [
    "Ask HN: Who is hiring",
    "Ask HN: Who's hiring",
    "Ask HN: Who wants to be hired?",
]
for year, month in product(years, months):
    month_year = f"{month} {year}"
    logger.info(month_year)
    search_response = httpx.get(
        "https://hn.algolia.com/api/v1/search",
        # Filter for a specific author with tag `f"author_{username}"`.
        # Turns out early posts were not published by `whoishiring` though
        params={"query": f"Ask HN {month_year}", "tags": "story"},
    )
    search_response = msgspec.json.decode(search_response.content, type=SearchResponse)
    for hit, query in product(search_response.hits, queries):
        norm_query = re.sub(r"\s+", " ", query).lower()
        norm_title = hit.title.strip().lower()
        if (norm_query in norm_title) and (month_year.lower() in norm_title):
            logger.info(f"{hit.title!r} found!")
            item_response = httpx.get(
                f"https://hn.algolia.com/api/v1/items/{hit.story_id}"
            )
            item_response = msgspec.json.decode(
                item_response.content, type=ItemResponse
            )
            for child in item_response.children:
                row = {
                    "story_id": hit.story_id,
                    "story_title": hit.title,
                    "story_author": hit.author,
                    "comment_id": child.story_id,
                    "comment_author": child.author,
                    "comment_text": child.text,
                }
                # TODO: recurse into child comments here
                print(json.dumps(row))
