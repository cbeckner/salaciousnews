"""
News Actions Lambda — Bedrock Flow node.

Receives: {} (any trigger object)
Returns:  {"headlines": [{id, title, url, source, category, published_at}, ...]}
"""

import hashlib
import json
import os
import time
from typing import Any

import boto3
import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Secrets
# ---------------------------------------------------------------------------
_secrets_client = boto3.client("secretsmanager")
_secret_cache: dict[str, str] = {}


def _get_secret(name: str) -> str:
    if name not in _secret_cache:
        resp = _secrets_client.get_secret_value(SecretId=name)
        _secret_cache[name] = resp["SecretString"]
    return _secret_cache[name]


def _news_api_key() -> str:
    return _get_secret(os.environ["NEWS_API_KEY_SECRET"])


# ---------------------------------------------------------------------------
# HTTP session
# ---------------------------------------------------------------------------
_session = requests.Session()
_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept-Encoding": "gzip, deflate",
})


def _get_with_retry(url: str, params: dict | None = None, max_attempts: int = 3,
                    timeout: int = 10) -> requests.Response:
    delay = 1.0
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            resp = _session.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < max_attempts - 1:
                time.sleep(delay)
                delay *= 2
    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Business logic
# ---------------------------------------------------------------------------
CATEGORY_MAP = {
    "Business": "business",
    "Entertainment": "entertainment",
    "Sports": "sports",
    "Technology": "technology",
    "Health": "health",
    "Science": "science",
    "General": "general",
}


def _make_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]


def fetch_headlines(num_articles: int = 20) -> dict:
    """
    Fetch top headlines from NewsAPI across multiple categories.
    Returns a larger pool (default 20) so PrepareArticles can select the best 3.

    Pulls a per-category share of the pool first so every category gets at
    least a couple of headlines, instead of filling the whole pool from
    whichever categories happen to come first in CATEGORY_MAP (which used to
    starve everything after Business/Entertainment).
    """
    api_key = _news_api_key()
    headlines: list[dict] = []
    seen: set[str] = set()

    per_category_cap = max(2, num_articles // len(CATEGORY_MAP))

    for cat, api_cat in CATEGORY_MAP.items():
        params = {
            "country": "us",
            "category": api_cat,
            "pageSize": 10,
            "apiKey": api_key,
        }
        added_for_category = 0
        try:
            resp = _get_with_retry("https://newsapi.org/v2/top-headlines", params=params)
            for art in resp.json().get("articles", []):
                if added_for_category >= per_category_cap:
                    break
                src_url = art.get("url", "")
                if not src_url or src_url in seen:
                    continue
                seen.add(src_url)
                headlines.append({
                    "id": _make_id(src_url),
                    "title": art.get("title", ""),
                    "url": src_url,
                    "source": (art.get("source") or {}).get("name", "Unknown"),
                    "category": cat,
                    "published_at": art.get("publishedAt", ""),
                })
                added_for_category += 1
        except Exception as exc:
            print(f"[news_actions] Warning: failed to fetch {cat}: {exc}")

    # If the per-category caps left room in the pool, top it off with any
    # leftover headlines (round 2, beyond each category's initial cap).
    if len(headlines) < num_articles:
        for cat, api_cat in CATEGORY_MAP.items():
            if len(headlines) >= num_articles:
                break
            params = {
                "country": "us",
                "category": api_cat,
                "pageSize": 10,
                "apiKey": api_key,
            }
            try:
                resp = _get_with_retry("https://newsapi.org/v2/top-headlines", params=params)
                for art in resp.json().get("articles", []):
                    if len(headlines) >= num_articles:
                        break
                    src_url = art.get("url", "")
                    if not src_url or src_url in seen:
                        continue
                    seen.add(src_url)
                    headlines.append({
                        "id": _make_id(src_url),
                        "title": art.get("title", ""),
                        "url": src_url,
                        "source": (art.get("source") or {}).get("name", "Unknown"),
                        "category": cat,
                        "published_at": art.get("publishedAt", ""),
                    })
            except Exception as exc:
                print(f"[news_actions] Warning: failed to top off {cat}: {exc}")

    print(f"[news_actions] Fetched {len(headlines)} headlines")
    return {"headlines": headlines[:num_articles]}


# ---------------------------------------------------------------------------
# Bedrock Flows input parser
# ---------------------------------------------------------------------------
def _flow_inputs(event: dict) -> dict:
    """
    Bedrock Flows wraps Lambda inputs in event["node"]["inputs"].
    Returns a flat dict of {name: value}.
    Falls back to the raw event for direct-invocation testing.
    """
    raw_inputs = event.get("node", {}).get("inputs", [])
    if raw_inputs:
        return {inp["name"]: inp["value"] for inp in raw_inputs}
    return event  # direct invocation


# ---------------------------------------------------------------------------
# Lambda entry point
# ---------------------------------------------------------------------------
def handler(event: dict, context: Any) -> dict:
    print(f"[news_actions] Invoked. event keys: {list(event.keys())}")
    inputs = _flow_inputs(event)
    num = int(inputs.get("num_articles", 20))
    return fetch_headlines(num)
