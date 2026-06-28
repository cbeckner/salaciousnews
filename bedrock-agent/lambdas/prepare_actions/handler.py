"""
Prepare Actions Lambda — Bedrock Flow node.

Receives: {"headlines": [{id, title, url, source, category, published_at}, ...]}

Steps:
  1. Ask DeepSeek to select 7 candidate article URLs from the headlines (buffer for dedup)
  2. Filter out URLs already seen in DynamoDB
  3. Scrape full text from the top 3 unseen URLs
  4. Ask DeepSeek to rewrite the articles in SalaciousNews tabloid style
  5. Write the used URLs to DynamoDB with a 90-day TTL

Returns: {
  "articles": [
    {
      "title": str,
      "slug": str,
      "category": str,
      "content": str,
      "description": str,
      "tags": [str],
      "teaser": str,
      "image_prompt": str,
      "source": str,
      "original_url": str
    }
  ]
}
"""

import json
import os
import re
import time
import unicodedata
from datetime import datetime, timezone, timedelta
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key
import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------
_bedrock = boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1"))
_dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))

SEEN_URLS_TABLE = os.environ.get("SEEN_URLS_TABLE", "salaciousnews-seen-urls")
SEEN_URL_TTL_DAYS = int(os.environ.get("SEEN_URL_TTL_DAYS", "90"))

FOUNDATION_MODEL_ID = os.environ.get("FOUNDATION_MODEL_ID", "deepseek.v3.2")
MIN_CONTENT_CHARS = int(os.environ.get("ARTICLE_MIN_LENGTH", "300"))

# ---------------------------------------------------------------------------
# HTTP session for scraping
# ---------------------------------------------------------------------------
_session = requests.Session()
_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
})


def _get_with_retry(url: str, max_attempts: int = 3, timeout: int = 12) -> requests.Response:
    delay = 1.0
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            resp = _session.get(url, timeout=timeout, allow_redirects=True)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < max_attempts - 1:
                time.sleep(delay)
                delay *= 2
    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# DeepSeek via Bedrock
# ---------------------------------------------------------------------------
def _call_deepseek(prompt: str, max_tokens: int = 4000, temperature: float = 0.7) -> str:
    """
    Call DeepSeek V3 via Bedrock converse API.
    Falls back to invoke_model with native DeepSeek format if needed.
    """
    try:
        resp = _bedrock.converse(
            modelId=FOUNDATION_MODEL_ID,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
        )
        return resp["output"]["message"]["content"][0]["text"]
    except Exception as exc:
        # Fallback: try native DeepSeek invoke_model format
        print(f"[prepare_actions] converse() failed ({exc}); trying invoke_model")
        body = json.dumps({
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        })
        resp = _bedrock.invoke_model(
            modelId=FOUNDATION_MODEL_ID,
            body=body,
            contentType="application/json",
            accept="application/json",
        )
        result = json.loads(resp["body"].read())
        # DeepSeek native response format
        return result["choices"][0]["message"]["content"]


def _extract_json(text: str) -> Any:
    """Extract a JSON object or array from potentially noisy LLM output."""
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Find JSON object or array in the text
    for pattern in [r'\{[\s\S]*\}', r'\[[\s\S]*\]']:
        match = re.search(pattern, text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                continue
    raise ValueError(f"Could not extract JSON from: {text[:200]}")


# ---------------------------------------------------------------------------
# Article scraping
# ---------------------------------------------------------------------------
def _scrape(url: str) -> dict:
    """Scrape article text from a URL. Returns {title, content, accessible}."""
    try:
        resp = _get_with_retry(url, timeout=12)
    except Exception as exc:
        print(f"[prepare_actions] Could not fetch {url}: {exc}")
        return {"url": url, "title": "", "content": "", "accessible": False}

    soup = BeautifulSoup(resp.content, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else ""

    paragraphs = [p.get_text(strip=True) for p in soup.find_all("p") if p.get_text(strip=True)]
    content = "\n\n".join(paragraphs)

    return {
        "url": url,
        "title": title,
        "content": content[:8000],
        "accessible": len(content) >= MIN_CONTENT_CHARS,
    }


# ---------------------------------------------------------------------------
# Slug helper
# ---------------------------------------------------------------------------
def _slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text)[:80]


# ---------------------------------------------------------------------------
# DynamoDB deduplication helpers
# ---------------------------------------------------------------------------
def _get_seen_table():
    return _dynamodb.Table(SEEN_URLS_TABLE)


def _filter_seen_urls(selections: list[dict]) -> list[dict]:
    """
    Remove any selections whose URL has already been processed.
    Uses DynamoDB batch_get_item for efficiency.
    """
    if not selections:
        return []

    table = _get_seen_table()
    urls = [s["url"] for s in selections]

    try:
        response = _dynamodb.batch_get_item(
            RequestItems={
                SEEN_URLS_TABLE: {
                    "Keys": [{"url": u} for u in urls],
                    "ProjectionExpression": "#u",
                    "ExpressionAttributeNames": {"#u": "url"},
                }
            }
        )
        seen = {item["url"] for item in response.get("Responses", {}).get(SEEN_URLS_TABLE, [])}
    except Exception as exc:
        print(f"[prepare_actions] DynamoDB read failed (proceeding without dedup): {exc}")
        seen = set()

    unseen = [s for s in selections if s["url"] not in seen]
    skipped = len(selections) - len(unseen)
    if skipped:
        print(f"[prepare_actions] Dedup: skipped {skipped} already-seen URL(s)")
    return unseen


def _mark_urls_seen(urls: list[str]) -> None:
    """Write each URL to DynamoDB with a 90-day TTL."""
    if not urls:
        return

    table = _get_seen_table()
    expires_at = int((datetime.now(timezone.utc) + timedelta(days=SEEN_URL_TTL_DAYS)).timestamp())
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        with table.batch_writer() as batch:
            for url in urls:
                batch.put_item(Item={
                    "url": url,
                    "seen_at": now_iso,
                    "expires_at": expires_at,
                })
        print(f"[prepare_actions] Marked {len(urls)} URL(s) as seen (TTL {SEEN_URL_TTL_DAYS}d)")
    except Exception as exc:
        # Non-fatal — don't fail the pipeline over a dedup write error
        print(f"[prepare_actions] Warning: DynamoDB write failed: {exc}")


# ---------------------------------------------------------------------------
# Step 1: Select candidate articles (request more than needed for dedup buffer)
# ---------------------------------------------------------------------------
def _select_articles(headlines: list[dict], num: int = 7) -> list[dict]:
    """
    Ask DeepSeek to pick `num` diverse candidates.
    We request more than 3 so that after filtering seen URLs we still have
    enough to fill 3 slots.
    """
    headlines_json = json.dumps(
        [{"url": h["url"], "title": h["title"], "category": h["category"], "source": h["source"]}
         for h in headlines],
        indent=2
    )

    categories_present = sorted({h["category"] for h in headlines if h.get("category")})

    prompt = f"""You are an editor for SalaciousNews, a satirical tabloid that rewrites real news in a scandalous, over-the-top gossip style.

Here are today's top headlines:
{headlines_json}

Select exactly {num} articles ranked by their potential for scandalous, humorous, or dramatic tabloid rewriting.

Category diversity is required, not optional: the headlines span these categories — {", ".join(categories_present)}. Pick at least one article from EVERY category listed above before picking a second from any single category. Do not let one category (e.g. Entertainment) dominate the selection.

Return ONLY valid JSON with this exact structure:
{{
  "selections": [
    {{"url": "...", "category": "...", "source": "...", "original_title": "..."}},
    ...
  ]
}}"""

    print(f"[prepare_actions] Selecting {num} candidate articles with DeepSeek...")
    response_text = _call_deepseek(prompt, max_tokens=1200, temperature=0.8)
    data = _extract_json(response_text)
    selections = data.get("selections", data) if isinstance(data, dict) else data
    print(f"[prepare_actions] Got {len(selections)} candidates")
    return selections[:num]


# ---------------------------------------------------------------------------
# Step 2: Scrape selected articles
# ---------------------------------------------------------------------------
def _scrape_selected(selections: list[dict]) -> list[dict]:
    """Scrape content for each selected article."""
    scraped = []
    for sel in selections:
        url = sel.get("url", "")
        print(f"[prepare_actions] Scraping: {url[:80]}")
        result = _scrape(url)
        result["category"] = sel.get("category", "General")
        result["source"] = sel.get("source", "Unknown")
        result["original_title"] = sel.get("original_title", result["title"])
        scraped.append(result)
    return scraped


# ---------------------------------------------------------------------------
# Step 3: Rewrite articles in salacious style
# ---------------------------------------------------------------------------
def _rewrite_articles(scraped: list[dict]) -> list[dict]:
    """Ask DeepSeek to rewrite articles in SalaciousNews tabloid style."""
    articles_json = json.dumps(
        [{"title": a["title"] or a.get("original_title", ""),
          "content": a["content"],
          "category": a["category"],
          "source": a["source"],
          "url": a["url"]}
         for a in scraped],
        indent=2
    )

    prompt = f"""You are a sensationalist tabloid writer for SalaciousNews. Rewrite the following news articles in an exaggerated, scandalous gossip style — think Page Six meets a prestige gossip column. Go big: lean into scandalous subtext, innuendo, and dramatic flair. For non-political stories (entertainment, sports, business, tech, health, science, general), feel free to be as cheeky, gossipy, and over-the-top as the story allows — don't hold back for the sake of restraint. Reserve extra care only for genuinely political/government stories, where you should keep the satire sharp but avoid outright false factual claims.

Title style rules (critical):
- Use title case (capitalize main words, not every word)
- Maximum 10 words — punchy, not exhausting
- No ALL CAPS words — emphasis comes from word choice, not caps lock
- Lead with the most scandalous detail, not the source name
- Only if needed, use a colon for a dramatic pivot, e.g. "Stars Bail on Trump Concert: He Stars in It Himself"
- Do NOT use an em-dash, en-dash, or any "—"/"–" character anywhere in the title
- Think New York Post front page: one killer line that makes you need to read more

Articles to rewrite:
{articles_json}

For each article, produce:
- A scandalous tabloid title following the style rules above
- A URL-safe slug (lowercase, hyphens, max 60 chars)
- Full rewritten article body (400-600 words, multiple paragraphs)
- A 1-sentence teaser for social media (punchy and clickbait-y, no ALL CAPS)
- A meta description for search engines: ONE sentence, plain text (no markdown), maximum 155 characters total
- 3-5 relevant tags
- A DALL-E image prompt for a dramatic photorealistic editorial image representing the story (no text, no logos, no people's faces)

Return ONLY valid JSON with this exact structure:
{{
  "articles": [
    {{
      "title": "Scandalous Headline in Title Case Here",
      "slug": "url-safe-slug-here",
      "category": "Entertainment",
      "content": "Full article body here...",
      "description": "Meta description here (<=155 chars, one sentence, plain text).",
      "teaser": "Clickbait teaser here.",
      "tags": ["tag1", "tag2", "tag3"],
      "image_prompt": "DALL-E prompt here",
      "source": "Original Source Name",
      "original_url": "https://original-url-here"
    }}
  ]
}}"""

    print("[prepare_actions] Rewriting articles with DeepSeek...")
    response_text = _call_deepseek(prompt, max_tokens=6000, temperature=0.9)
    data = _extract_json(response_text)
    articles = data.get("articles", []) if isinstance(data, dict) else data

    # Ensure slugs are valid and unique
    seen_slugs: set[str] = set()
    for art in articles:
        slug = _slugify(art.get("slug", art.get("title", "article")))
        if slug in seen_slugs:
            slug = f"{slug}-{len(seen_slugs)}"
        seen_slugs.add(slug)
        art["slug"] = slug
        # Ensure list fields
        if isinstance(art.get("tags"), str):
            art["tags"] = [t.strip() for t in art["tags"].split(",") if t.strip()]
        # Strip em/en-dashes — the social/article-image font may render them as
        # missing-glyph boxes; a colon reads just as well for a dramatic pivot.
        for field in ("title", "teaser"):
            if art.get(field):
                art[field] = art[field].replace("—", ":").replace("–", ":")

    print(f"[prepare_actions] Rewrote {len(articles)} articles")
    return articles


# ---------------------------------------------------------------------------
# Bedrock Flows input parser
# ---------------------------------------------------------------------------
def _flow_inputs(event: dict) -> dict:
    raw_inputs = event.get("node", {}).get("inputs", [])
    if raw_inputs:
        return {inp["name"]: inp["value"] for inp in raw_inputs}
    return event  # direct invocation


# ---------------------------------------------------------------------------
# Lambda entry point
# ---------------------------------------------------------------------------
def handler(event: dict, context: Any) -> dict:
    print(f"[prepare_actions] Invoked. event keys: {list(event.keys())}")
    inputs = _flow_inputs(event)

    headlines = inputs.get("headlines", [])
    if not headlines:
        raise ValueError("No headlines provided in event")

    print(f"[prepare_actions] Received {len(headlines)} headlines")

    # Step 1: Select candidates (one per category plus a buffer so dedup still leaves us 3)
    num_categories = len({h["category"] for h in headlines if h.get("category")}) or 7
    candidates = _select_articles(headlines, num=num_categories + 2)

    # Step 2: Filter out already-seen URLs
    unseen = _filter_seen_urls(candidates)
    if not unseen:
        print("[prepare_actions] Warning: all candidates already seen — using top 3 anyway")
        unseen = candidates[:3]
    elif len(unseen) < 3:
        print(f"[prepare_actions] Only {len(unseen)} unseen candidate(s); proceeding with fewer")

    selections = unseen[:3]
    print(f"[prepare_actions] Using {len(selections)} unseen article(s)")

    # Step 3: Scrape content
    scraped = _scrape_selected(selections)
    accessible = [a for a in scraped if a.get("accessible")]
    if not accessible:
        accessible = scraped
        print("[prepare_actions] Warning: no articles had sufficient content, using all scraped")

    # Step 4: Rewrite
    articles = _rewrite_articles(accessible)

    if not articles:
        raise RuntimeError("DeepSeek returned no articles")

    # Step 5: Mark the used URLs as seen in DynamoDB
    used_urls = [s["url"] for s in selections[:len(accessible)]]
    _mark_urls_seen(used_urls)

    return {"articles": articles}
