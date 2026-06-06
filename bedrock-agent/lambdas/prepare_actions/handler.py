"""
Prepare Actions Lambda — Bedrock Flow node.

Receives: {"headlines": [{id, title, url, source, category, published_at}, ...]}

Steps:
  1. Ask DeepSeek to select 3 diverse, interesting article URLs from the headlines
  2. Scrape full text from those 3 URLs
  3. Ask DeepSeek to rewrite the articles in SalaciousNews tabloid style

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
from typing import Any

import boto3
import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------
_bedrock = boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1"))

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
# Step 1: Select 3 articles
# ---------------------------------------------------------------------------
def _select_articles(headlines: list[dict]) -> list[dict]:
    """Ask DeepSeek to pick 3 diverse, interesting articles."""
    headlines_json = json.dumps(
        [{"url": h["url"], "title": h["title"], "category": h["category"], "source": h["source"]}
         for h in headlines],
        indent=2
    )

    prompt = f"""You are an editor for SalaciousNews, a satirical tabloid that rewrites real news in a scandalous, over-the-top gossip style.

Here are today's top headlines:
{headlines_json}

Select exactly 3 articles that have the MOST potential for scandalous, humorous, or dramatic tabloid rewriting. Choose articles from different categories when possible.

Return ONLY valid JSON with this exact structure:
{{
  "selections": [
    {{"url": "...", "category": "...", "source": "...", "original_title": "..."}},
    {{"url": "...", "category": "...", "source": "...", "original_title": "..."}},
    {{"url": "...", "category": "...", "source": "...", "original_title": "..."}}
  ]
}}"""

    print("[prepare_actions] Selecting 3 articles with DeepSeek...")
    response_text = _call_deepseek(prompt, max_tokens=800, temperature=0.8)
    data = _extract_json(response_text)
    selections = data.get("selections", data) if isinstance(data, dict) else data
    print(f"[prepare_actions] Selected {len(selections)} articles")
    return selections[:3]


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

    prompt = f"""You are a sensationalist tabloid writer for SalaciousNews. Rewrite the following news articles in an exaggerated, scandalous, over-the-top gossip style — think National Enquirer meets TMZ. Be dramatic, use ALL CAPS for emphasis occasionally, add scandalous subtext even to mundane stories, but keep them grounded in the real facts.

Articles to rewrite:
{articles_json}

For each article, produce:
- A scandalous tabloid title (headline-style)
- A URL-safe slug (lowercase, hyphens, max 60 chars)
- Full rewritten article body (400-600 words, multiple paragraphs)
- A 1-sentence teaser for social media (punchy and clickbait-y)
- A 1-2 sentence meta description
- 3-5 relevant tags
- A DALL-E image prompt for a dramatic photorealistic editorial image representing the story (no text, no logos, no people's faces)

Return ONLY valid JSON with this exact structure:
{{
  "articles": [
    {{
      "title": "SCANDALOUS HEADLINE HERE",
      "slug": "url-safe-slug-here",
      "category": "Entertainment",
      "content": "Full article body here...",
      "description": "Meta description here.",
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


    # Step 1: Select 3 articles
    selections = _select_articles(headlines)

    # Step 2: Scrape content
    scraped = _scrape_selected(selections)
    accessible = [a for a in scraped if a.get("accessible")]
    if not accessible:
        # Fall back to all scraped even if short
        accessible = scraped
        print("[prepare_actions] Warning: no articles had sufficient content, using all scraped")

    # Step 3: Rewrite
    articles = _rewrite_articles(accessible)

    if not articles:
        raise RuntimeError("DeepSeek returned no articles")

    return {"articles": articles}
