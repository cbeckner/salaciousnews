"""
Publish Actions Lambda — Bedrock Flow node.

Receives: {
  "article": {title, slug, category, content, description, tags, teaser,
              image_prompt, source, original_url},
  "image_info": {s3_key, filename, hugo_image_path}
}

Returns: {"github_file_path": str, "article_url": str, "already_existed": bool}
"""

import base64
import json
import os
import time
from datetime import datetime, timezone
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
GITHUB_REPO = os.environ["GITHUB_REPO"]
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main")
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://salacious.news").rstrip("/")
GITHUB_TOKEN_SECRET = os.environ["GITHUB_TOKEN_SECRET"]


def _get_secret(name: str) -> str:
    if name not in _secret_cache:
        resp = _secrets.get_secret_value(SecretId=name)
        _secret_cache[name] = resp["SecretString"]
    return _secret_cache[name]


def _github_headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_secret(GITHUB_TOKEN_SECRET)}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


# ---------------------------------------------------------------------------
# GitHub helpers
# ---------------------------------------------------------------------------
def _github_get_file_sha(path: str) -> str | None:
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    resp = requests.get(url, headers=_github_headers(), params={"ref": GITHUB_BRANCH}, timeout=15)
    if resp.status_code == 200:
        return resp.json().get("sha")
    return None


def _github_put_file(path: str, content_bytes: bytes, message: str,
                     existing_sha: str | None = None) -> dict:
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    payload: dict[str, Any] = {
        "message": message,
        "content": base64.b64encode(content_bytes).decode(),
        "branch": GITHUB_BRANCH,
    }
    if existing_sha:
        payload["sha"] = existing_sha

    delay = 2.0
    for attempt in range(3):
        resp = requests.put(url, headers=_github_headers(), json=payload, timeout=30)
        if resp.status_code in (200, 201):
            return resp.json()
        if resp.status_code == 409 and attempt < 2:
            print(f"[publish_actions] 409 conflict on {path}; re-fetching SHA")
            payload["sha"] = _github_get_file_sha(path)
            time.sleep(delay)
            delay *= 2
            continue
        resp.raise_for_status()

    raise RuntimeError(f"GitHub PUT failed for {path} after retries")


# ---------------------------------------------------------------------------
# Markdown / frontmatter generation
# ---------------------------------------------------------------------------
def _format_tags(tags: list[str]) -> str:
    return "\n".join(f"- {t}" for t in tags) if tags else ""


def _build_markdown(article: dict, image_filename: str) -> str:
    date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.0000000Z")
    image_path = f"./img/posts/{image_filename}"
    tags_yaml = _format_tags(article.get("tags", []))
    frontmatter = f"""---
Title: "{article['title']}"
Description: "{article.get('description', '')}"
Date: {date}
Categories:
- {article['category']}
Tags:
{tags_yaml}
Featured: true
Thumbnail:
  Src: {image_path}
  Visibility:
  - post
ImagePrompt: "{article.get('image_prompt', '')}"
Source: {article.get('source', 'Unknown')}
OriginalUrl: {article.get('original_url', '')}

---
"""
    return frontmatter + article["content"]


# ---------------------------------------------------------------------------
# Main publish logic
# ---------------------------------------------------------------------------
def publish_article(article: dict, image_info: dict) -> dict:
    slug = article["slug"]
    category = article["category"]
    image_s3_key = image_info["s3_key"]
    image_filename = image_info["filename"]

    # 1. Download image from S3
    print(f"[publish_actions] Downloading image from s3://{BUCKET}/{image_s3_key}")
    img_obj = _s3.get_object(Bucket=BUCKET, Key=image_s3_key)
    image_bytes = img_obj["Body"].read()

    # 2. Commit image to GitHub
    img_repo_path = f"static/img/posts/{image_filename}"
    existing_img_sha = _github_get_file_sha(img_repo_path)
    already_existed = existing_img_sha is not None
    _github_put_file(img_repo_path, image_bytes,
                     f"chore: add article image {image_filename}", existing_img_sha)
    print(f"[publish_actions] Image committed: {img_repo_path}")

    # 3. Build and commit markdown
    markdown = _build_markdown(article, image_filename)
    md_repo_path = f"content/{category}/{slug}.md"
    existing_md_sha = _github_get_file_sha(md_repo_path)
    _github_put_file(md_repo_path, markdown.encode("utf-8"),
                     f"content: publish '{article['title']}'", existing_md_sha)
    print(f"[publish_actions] Markdown committed: {md_repo_path}")

    article_url = f"{SITE_BASE_URL}/{category.lower()}/{slug}/"
    return {
        "github_file_path": md_repo_path,
        "article_url": article_url,
        "already_existed": already_existed,
    }


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
    print(f"[publish_actions] Invoked. event keys: {list(event.keys())}")
    inputs = _flow_inputs(event)

    article = inputs.get("article", {})
    image_info = inputs.get("image_info", {})

    # Validate required fields
    required_article = ["slug", "category", "title", "content"]
    missing = [k for k in required_article if not article.get(k)]
    if missing:
        raise ValueError(f"Missing required article fields: {missing}")

    if not image_info.get("s3_key") or not image_info.get("filename"):
        raise ValueError("image_info must contain s3_key and filename")

    # Ensure tags is a list
    tags = article.get("tags", [])
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except Exception:
            tags = [t.strip() for t in tags.split(",") if t.strip()]
    article = {**article, "tags": tags}

    return publish_article(article, image_info)
