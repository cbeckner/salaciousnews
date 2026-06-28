"""
Social Actions Lambda — Bedrock Flow node (runs ONCE after BatchPublish).

Receives the full batch_result from BatchPublish. Among the articles that
have a social image, asks DeepSeek (via Bedrock) to rank them by viral
potential and posts the top 2 to Instagram.

Receives:
  batch_result (Object) — {
    articles: [{article_url, slug, title, teaser, social_s3_key}, ...],
    commit_sha: str,
    files_committed: int
  }

Returns: {"skipped": bool, "platform": "instagram",
          "posts": [{"slug": str, "post_id": str}, ...]}
"""

import json
import os
import re
import time
from typing import Any

import boto3
import requests

# ---------------------------------------------------------------------------
# Clients / config
# ---------------------------------------------------------------------------
_s3 = boto3.client("s3")
_secrets = boto3.client("secretsmanager")
_bedrock = boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1"))
_secret_cache: dict[str, str] = {}

BUCKET = os.environ["IMAGES_BUCKET"]
INSTAGRAM_TOKEN_SECRET = os.environ["INSTAGRAM_TOKEN_SECRET"]
INSTAGRAM_USER_ID_SECRET = os.environ["INSTAGRAM_USER_ID_SECRET"]
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://salacious.news").rstrip("/")
FOUNDATION_MODEL_ID = os.environ.get("FOUNDATION_MODEL_ID", "deepseek.v3.2")
PRESIGN_TTL_SECONDS = 900
VIRAL_POST_COUNT = 2


def _get_secret(name: str) -> str:
    if name not in _secret_cache:
        _secret_cache[name] = _secrets.get_secret_value(SecretId=name)["SecretString"]
    return _secret_cache[name]


def _instagram_credentials() -> tuple[str, str] | None:
    placeholders = {"", "your_instagram_user_id", "your_access_token"}
    try:
        token = _get_secret(INSTAGRAM_TOKEN_SECRET)
        user_id = _get_secret(INSTAGRAM_USER_ID_SECRET)
    except Exception as exc:
        print(f"[social_actions] Could not retrieve Instagram secrets: {exc}")
        return None
    if token.lower() in placeholders or user_id.lower() in placeholders:
        return None
    return token, user_id


# ---------------------------------------------------------------------------
# DeepSeek viral-potential ranking
# ---------------------------------------------------------------------------
def _call_deepseek(prompt: str, max_tokens: int = 500, temperature: float = 0.3) -> str:
    try:
        resp = _bedrock.converse(
            modelId=FOUNDATION_MODEL_ID,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
        )
        return resp["output"]["message"]["content"][0]["text"]
    except Exception as exc:
        print(f"[social_actions] converse() failed ({exc}); trying invoke_model")
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
        return result["choices"][0]["message"]["content"]


def _extract_json(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for pattern in [r'\{[\s\S]*\}', r'\[[\s\S]*\]']:
        match = re.search(pattern, text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                continue
    raise ValueError(f"Could not extract JSON from: {text[:200]}")


def _select_viral_candidates(articles: list[dict], top_n: int = VIRAL_POST_COUNT) -> list[dict]:
    """Rank articles by viral potential via DeepSeek and return the top N.

    Falls back to the first N articles (in their existing order) if the
    model call or JSON parsing fails — never blocks posting entirely.
    """
    if len(articles) <= top_n:
        return articles

    candidates = [
        {"slug": a.get("slug", ""), "title": a.get("title", ""), "teaser": a.get("teaser", "")}
        for a in articles
    ]
    prompt = f"""You are a social media strategist for a tabloid gossip site. Below are
{len(candidates)} candidate articles published today. Rank them by how likely they are to
go viral on Instagram (engagement, shareability, shock value, broad appeal).

Candidates:
{json.dumps(candidates, indent=2)}

Return ONLY a JSON array of the {top_n} best slugs, ordered best-first, e.g.:
["slug-one", "slug-two"]"""

    try:
        response_text = _call_deepseek(prompt)
        ranked_slugs = _extract_json(response_text)
        if not isinstance(ranked_slugs, list):
            raise ValueError(f"Expected a JSON array of slugs, got: {ranked_slugs!r}")

        by_slug = {a.get("slug"): a for a in articles}
        selected = [by_slug[slug] for slug in ranked_slugs if slug in by_slug][:top_n]
        if selected:
            print(f"[social_actions] Viral ranking selected: {[a.get('slug') for a in selected]}")
            return selected
        raise ValueError("None of the ranked slugs matched a candidate article")
    except Exception as exc:
        print(f"[social_actions] Viral ranking failed ({exc}); falling back to first {top_n}")
        return articles[:top_n]


# ---------------------------------------------------------------------------
# Bedrock Flows input parser
# ---------------------------------------------------------------------------
def _flow_inputs(event: dict) -> dict:
    raw = event.get("node", {}).get("inputs", [])
    if raw:
        return {inp["name"]: inp["value"] for inp in raw}
    return event


# ---------------------------------------------------------------------------
# Instagram posting
# ---------------------------------------------------------------------------
def _post_with_retry(url: str, data: dict, max_attempts: int = 3) -> requests.Response:
    delay = 2.0
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            resp = requests.post(url, data=data, timeout=20)
            return resp
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < max_attempts - 1:
                time.sleep(delay)
                delay *= 2
    raise last_exc  # type: ignore[misc]


def _wait_for_container_ready(container_id: str, token: str, max_attempts: int = 10, delay: float = 2.0) -> None:
    """Poll the media container's status_code until FINISHED (or give up after max_attempts)."""
    for attempt in range(max_attempts):
        resp = requests.get(
            f"https://graph.instagram.com/v21.0/{container_id}",
            params={"fields": "status_code", "access_token": token},
            timeout=20,
        )
        status = resp.json().get("status_code") if resp.ok else None
        print(f"[social_actions] Container {container_id} status: {status} (attempt {attempt + 1}/{max_attempts})")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"Instagram container processing failed: {resp.text}")
        time.sleep(delay)
    print(f"[social_actions] Container {container_id} not FINISHED after {max_attempts} attempts; attempting publish anyway")


def post_to_instagram(social_image_s3_key: str, caption: str, article_url: str) -> dict:
    creds = _instagram_credentials()
    if not creds:
        print("[social_actions] Instagram not configured; skipping")
        return {"skipped": True, "platform": "instagram", "post_id": None}

    if not social_image_s3_key:
        print("[social_actions] No social image; skipping")
        return {"skipped": True, "platform": "instagram", "post_id": None}

    token, user_id = creds

    image_url = _s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET, "Key": social_image_s3_key},
        ExpiresIn=PRESIGN_TTL_SECONDS,
    )

    full_caption = f"{caption}\n\nRead more: {article_url}\n\n#SalaciousNews #BreakingNews"

    container_resp = _post_with_retry(
        f"https://graph.instagram.com/v21.0/{user_id}/media",
        {"image_url": image_url, "caption": full_caption, "access_token": token},
    )
    if not container_resp.ok:
        raise RuntimeError(
            f"Instagram container failed ({container_resp.status_code}): {container_resp.text}"
        )
    container_id = container_resp.json()["id"]
    print(f"[social_actions] Container created: {container_id}")

    _wait_for_container_ready(container_id, token)

    publish_resp = _post_with_retry(
        f"https://graph.instagram.com/v21.0/{user_id}/media_publish",
        {"creation_id": container_id, "access_token": token},
    )
    if not publish_resp.ok:
        raise RuntimeError(
            f"Instagram publish failed ({publish_resp.status_code}): {publish_resp.text}"
        )
    post_id = publish_resp.json().get("id")
    print(f"[social_actions] Published: {post_id}")
    return {"skipped": False, "platform": "instagram", "post_id": post_id}


# ---------------------------------------------------------------------------
# Lambda entry point
# ---------------------------------------------------------------------------
def handler(event: dict, context: Any) -> dict:
    print(f"[social_actions] Invoked. event keys: {list(event.keys())}")
    inputs = _flow_inputs(event)

    batch_result = inputs.get("batch_result", {})
    articles = batch_result.get("articles", [])

    candidates = [a for a in articles if a.get("social_s3_key")]
    if not candidates:
        print("[social_actions] No articles with a social image; skipping")
        return {"skipped": True, "platform": "instagram", "posts": []}

    targets = _select_viral_candidates(candidates)

    posts = []
    any_success = False
    for i, target in enumerate(targets):
        slug = target.get("slug")
        social_s3_key = target.get("social_s3_key", "")
        article_url = target.get("article_url", "")
        caption = target.get("teaser") or target.get("title", "")

        print(f"[social_actions] Posting article {i + 1}/{len(targets)}: {slug}")
        try:
            result = post_to_instagram(social_s3_key, caption, article_url)
            posts.append({"slug": slug, **result})
            any_success = any_success or not result.get("skipped", True)
        except Exception as exc:
            print(f"[social_actions] Instagram post failed for '{slug}' (non-fatal): {exc}")
            posts.append({"slug": slug, "skipped": True, "post_id": None, "error": str(exc)})

        if i < len(targets) - 1:
            time.sleep(5)  # brief gap between posts

    return {"skipped": not any_success, "platform": "instagram", "posts": posts}
