"""
Batch Publish Lambda — Bedrock Flow node (runs ONCE after the Collector).

Uses the GitHub Git Trees API to commit every article's image and markdown
file in a SINGLE commit, no matter how many articles were generated.

One commit per pipeline run = one CI build trigger.

Receives:
  articles_bundle (Array) — list of per-article dicts, each containing:
    {
      "article":     {title, slug, category, content, description, tags,
                      teaser, image_prompt, source, original_url},
      "image_info":  {s3_key, filename, hugo_image_path},
      "social_s3_key": str   (may be "" if social image generation failed)
    }

Returns:
  {
    "articles": [
      {"article_url": str, "slug": str, "title": str,
       "teaser": str, "social_s3_key": str}
    ],
    "commit_sha":      str,
    "files_committed": int
  }
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
# Config / clients
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
        _secret_cache[name] = _secrets.get_secret_value(SecretId=name)["SecretString"]
    return _secret_cache[name]


def _github_headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_secret(GITHUB_TOKEN_SECRET)}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


# ---------------------------------------------------------------------------
# Bedrock Flows input parser
# ---------------------------------------------------------------------------
def _flow_inputs(event: dict) -> dict:
    raw = event.get("node", {}).get("inputs", [])
    if raw:
        return {inp["name"]: inp["value"] for inp in raw}
    return event


# ---------------------------------------------------------------------------
# Markdown / frontmatter
# ---------------------------------------------------------------------------
MAX_DESCRIPTION_LEN = 155


def _yaml_quote(value: str) -> str:
    """Escape and collapse a string for use in a YAML double-quoted scalar."""
    value = " ".join(value.split())  # collapse whitespace/newlines
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _build_description(article: dict) -> str:
    description = " ".join(article.get("description", "").split())
    if len(description) <= MAX_DESCRIPTION_LEN:
        return description
    truncated = description[:MAX_DESCRIPTION_LEN].rsplit(" ", 1)[0]
    return truncated.rstrip(",;: ") + "…"


def _build_markdown(article: dict, image_filename: str) -> str:
    date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.0000000Z")
    tags = article.get("tags", [])
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except Exception:
            tags = [t.strip() for t in tags.split(",") if t.strip()]
    tags_yaml = "\n".join(f"- {t}" for t in tags) if tags else ""

    return f"""---
Title: "{_yaml_quote(article['title'])}"
Description: "{_yaml_quote(_build_description(article))}"
Date: {date}
Categories:
- {article['category']}
Tags:
{tags_yaml}
Featured: true
Thumbnail:
  Src: ./img/posts/{image_filename}
  Visibility:
  - post
ImagePrompt: "{_yaml_quote(article.get('image_prompt', ''))}"
Source: {article.get('source', 'Unknown')}
OriginalUrl: {article.get('original_url', '')}

---
{article['content']}"""


# ---------------------------------------------------------------------------
# GitHub Trees API helpers
# ---------------------------------------------------------------------------
def _gh_get(path: str) -> dict:
    resp = requests.get(
        f"https://api.github.com/repos/{GITHUB_REPO}/{path}",
        headers=_github_headers(), timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def _gh_post(path: str, payload: dict, retries: int = 3) -> dict:
    delay = 2.0
    for attempt in range(retries):
        resp = requests.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/{path}",
            headers=_github_headers(), json=payload, timeout=30,
        )
        if resp.ok:
            return resp.json()
        if attempt < retries - 1:
            time.sleep(delay)
            delay *= 2
    resp.raise_for_status()
    return {}  # unreachable


def _gh_patch(path: str, payload: dict) -> dict:
    resp = requests.patch(
        f"https://api.github.com/repos/{GITHUB_REPO}/{path}",
        headers=_github_headers(), json=payload, timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def _create_blob(content_b64: str) -> str:
    """Upload a base64-encoded blob and return its SHA."""
    data = _gh_post("git/blobs", {"content": content_b64, "encoding": "base64"})
    return data["sha"]


# ---------------------------------------------------------------------------
# Main batch-publish logic
# ---------------------------------------------------------------------------
def batch_publish(bundles: list[dict]) -> dict:
    if not bundles:
        raise ValueError("No article bundles provided")

    # 1. Get current HEAD commit + base tree SHA
    ref = _gh_get(f"git/ref/heads/{GITHUB_BRANCH}")
    head_sha = ref["object"]["sha"]
    head_commit = _gh_get(f"git/commits/{head_sha}")
    base_tree_sha = head_commit["tree"]["sha"]
    print(f"[batch_publish] HEAD={head_sha[:8]}, base_tree={base_tree_sha[:8]}")

    # 2. Build the tree — create one blob per file for all articles
    tree_items = []
    article_results = []

    for bundle in bundles:
        article = bundle.get("article", {})
        image_info = bundle.get("image_info", {})
        social_s3_key = bundle.get("social_s3_key", "")

        slug = article.get("slug", "unknown")
        category = article.get("category", "General")
        image_filename = image_info.get("filename", "")
        image_s3_key = image_info.get("s3_key", "")

        if not image_s3_key or not image_filename:
            print(f"[batch_publish] Skipping {slug} — missing image info")
            continue

        # --- Image blob ---
        print(f"[batch_publish] Creating image blob for {slug}")
        img_bytes = _s3.get_object(Bucket=BUCKET, Key=image_s3_key)["Body"].read()
        img_blob_sha = _create_blob(base64.b64encode(img_bytes).decode())
        tree_items.append({
            "path": f"static/img/posts/{image_filename}",
            "mode": "100644",
            "type": "blob",
            "sha": img_blob_sha,
        })

        # --- Markdown blob ---
        print(f"[batch_publish] Creating markdown blob for {slug}")
        markdown = _build_markdown(article, image_filename)
        md_blob_sha = _create_blob(base64.b64encode(markdown.encode("utf-8")).decode())
        tree_items.append({
            "path": f"content/{category}/{slug}.md",
            "mode": "100644",
            "type": "blob",
            "sha": md_blob_sha,
        })

        article_url = f"{SITE_BASE_URL}/{category.lower()}/{slug}/"
        article_results.append({
            "article_url":   article_url,
            "slug":          slug,
            "title":         article.get("title", ""),
            "teaser":        article.get("teaser", ""),
            "social_s3_key": social_s3_key,
        })

    if not tree_items:
        raise RuntimeError("No valid articles to publish — all bundles were missing image info")

    # 3. Create the new tree
    n_articles = len(article_results)
    print(f"[batch_publish] Creating tree with {len(tree_items)} files for {n_articles} articles")
    new_tree = _gh_post("git/trees", {
        "base_tree": base_tree_sha,
        "tree": tree_items,
    })
    new_tree_sha = new_tree["sha"]

    # 4. Create ONE commit
    commit_msg = f"content: publish {n_articles} article{'s' if n_articles != 1 else ''}"
    new_commit = _gh_post("git/commits", {
        "message": commit_msg,
        "tree": new_tree_sha,
        "parents": [head_sha],
    })
    new_commit_sha = new_commit["sha"]
    print(f"[batch_publish] Created commit {new_commit_sha[:8]}: {commit_msg}")

    # 5. Advance the branch ref
    _gh_patch(f"git/refs/heads/{GITHUB_BRANCH}", {"sha": new_commit_sha})
    print(f"[batch_publish] Branch '{GITHUB_BRANCH}' advanced to {new_commit_sha[:8]}")

    return {
        "articles":        article_results,
        "commit_sha":      new_commit_sha,
        "files_committed": len(tree_items),
    }


# ---------------------------------------------------------------------------
# Lambda entry point
# ---------------------------------------------------------------------------
def handler(event: dict, context: Any) -> dict:
    print(f"[batch_publish] Invoked. event keys: {list(event.keys())}")
    inputs = _flow_inputs(event)

    bundles = inputs.get("articles_bundle", [])
    if not isinstance(bundles, list):
        raise ValueError(f"Expected 'articles_bundle' to be a list, got {type(bundles)}")

    print(f"[batch_publish] Publishing {len(bundles)} article(s) in one commit")
    return batch_publish(bundles)
