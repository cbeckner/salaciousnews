"""
Social Actions Lambda — Bedrock Flow node.

Receives: {
  "social_info":    {"s3_key": str, "filename": str},
  "publish_result": {"article_url": str, ...},
  "article":        {"teaser": str, "title": str, ...}
}

Returns: {"skipped": bool, "platform": "instagram", "post_id": str | None}
"""

import os
import time
from typing import Any

import boto3
import requests

# ---------------------------------------------------------------------------
# Clients / config
# ---------------------------------------------------------------------------
_s3 = boto3.client("s3")
_secrets = boto3.client("secretsmanager")
_secret_cache: dict[str, str] = {}

BUCKET = os.environ["IMAGES_BUCKET"]
INSTAGRAM_TOKEN_SECRET = os.environ["INSTAGRAM_TOKEN_SECRET"]
INSTAGRAM_USER_ID_SECRET = os.environ["INSTAGRAM_USER_ID_SECRET"]
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://salacious.news").rstrip("/")
PRESIGN_TTL_SECONDS = 900  # 15 min


def _get_secret(name: str) -> str:
    if name not in _secret_cache:
        resp = _secrets.get_secret_value(SecretId=name)
        _secret_cache[name] = resp["SecretString"]
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
# Instagram publish
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


def post_to_instagram(social_image_s3_key: str, caption: str, article_url: str) -> dict:
    creds = _instagram_credentials()
    if not creds:
        print("[social_actions] Instagram credentials not configured; skipping")
        return {"skipped": True, "platform": "instagram", "post_id": None}

    token, user_id = creds

    if not social_image_s3_key:
        print("[social_actions] No social image s3_key; skipping Instagram post")
        return {"skipped": True, "platform": "instagram", "post_id": None}

    image_url = _s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET, "Key": social_image_s3_key},
        ExpiresIn=PRESIGN_TTL_SECONDS,
    )
    print(f"[social_actions] Presigned URL generated (TTL {PRESIGN_TTL_SECONDS}s)")

    full_caption = f"{caption}\n\nRead more: {article_url}\n\n#SalaciousNews #BreakingNews"

    container_url = f"https://graph.facebook.com/v21.0/{user_id}/media"
    container_resp = _post_with_retry(container_url, {
        "image_url": image_url,
        "caption": full_caption,
        "access_token": token,
    })
    if not container_resp.ok:
        raise RuntimeError(
            f"Instagram container creation failed ({container_resp.status_code}): {container_resp.text}"
        )
    container_id = container_resp.json()["id"]
    print(f"[social_actions] Instagram container: {container_id}")

    publish_url = f"https://graph.facebook.com/v21.0/{user_id}/media_publish"
    publish_resp = _post_with_retry(publish_url, {
        "creation_id": container_id,
        "access_token": token,
    })
    if not publish_resp.ok:
        raise RuntimeError(
            f"Instagram publish failed ({publish_resp.status_code}): {publish_resp.text}"
        )
    post_id = publish_resp.json().get("id")
    print(f"[social_actions] Instagram post published: {post_id}")
    return {"skipped": False, "platform": "instagram", "post_id": post_id}


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
    print(f"[social_actions] Invoked. event keys: {list(event.keys())}")
    inputs = _flow_inputs(event)

    social_info = inputs.get("social_info", {})
    publish_result = inputs.get("publish_result", {})
    article = inputs.get("article", {})

    social_image_s3_key = social_info.get("s3_key", "")
    article_url = publish_result.get("article_url", "")
    caption = article.get("teaser", article.get("title", ""))

    try:
        return post_to_instagram(social_image_s3_key, caption, article_url)
    except Exception as exc:
        # Social posting is best-effort — don't fail the whole article pipeline
        print(f"[social_actions] Instagram post failed (non-fatal): {exc}")
        return {"skipped": True, "platform": "instagram", "post_id": None, "error": str(exc)}
