"""
Bundle Article Lambda — Bedrock Flow node (runs inside the Iterator).

Collects the per-article outputs from GenerateArticleImage and
GenerateSocialImage alongside the article data and bundles them into a
single object for the Collector node.

Receives:
  article        (Object) — full article dict from the Iterator
  image_info     (Object) — {s3_key, filename, hugo_image_path}
  social_s3_key  (String) — S3 key of the social overlay image (may be "")

Returns:
  {article, image_info, social_s3_key}
"""

from typing import Any


def _flow_inputs(event: dict) -> dict:
    raw = event.get("node", {}).get("inputs", [])
    if raw:
        return {inp["name"]: inp["value"] for inp in raw}
    return event  # direct-invocation fallback


def handler(event: dict, context: Any) -> dict:
    inputs = _flow_inputs(event)
    print(f"[bundle_article] Bundling article: {inputs.get('article', {}).get('slug', '?')}")
    return {
        "article":       inputs.get("article", {}),
        "image_info":    inputs.get("image_info", {}),
        "social_s3_key": inputs.get("social_s3_key", ""),
    }
