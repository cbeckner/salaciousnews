"""
Image Actions Lambda — Bedrock Flow node.

Detects which action to run based on input keys:
  - If event has "article_image_s3_key"  → generate_social_image
  - Otherwise                            → generate_article_image

generate_article_image
  Receives: {"article": {title, slug, image_prompt, ...}}
  Returns:  {"s3_key": str, "filename": str, "hugo_image_path": str}

generate_social_image
  Receives: {"article": {title, slug, ...}, "article_image_s3_key": str}
  Returns:  {"s3_key": str, "filename": str}
"""

import base64
import os
import time
import uuid
from io import BytesIO
from pathlib import Path
from typing import Any

import boto3
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Clients / config
# ---------------------------------------------------------------------------
_s3 = boto3.client("s3")
_secrets = boto3.client("secretsmanager")
_secret_cache: dict[str, str] = {}

BUCKET = os.environ["IMAGES_BUCKET"]
IMAGE_SIZE = os.environ.get("IMAGE_SIZE", "1536x1024")
IMAGE_QUALITY = os.environ.get("IMAGE_QUALITY", "standard")
IMAGE_MODEL = os.environ.get("OPENAI_IMAGE_MODEL", "chatgpt-image-latest")
OPENAI_MODEL_SECRET = os.environ["OPENAI_API_KEY_SECRET"]

LOGO_PATH = Path(__file__).parent / "logo.webp"


def _get_secret(name: str) -> str:
    if name not in _secret_cache:
        resp = _secrets.get_secret_value(SecretId=name)
        _secret_cache[name] = resp["SecretString"]
    return _secret_cache[name]


def _openai_client() -> OpenAI:
    return OpenAI(api_key=_get_secret(OPENAI_MODEL_SECRET))


# ---------------------------------------------------------------------------
# Article image generation
# ---------------------------------------------------------------------------
SAFE_FALLBACK_PROMPT = (
    "A professional newsroom scene with journalists working at modern desks, "
    "soft editorial lighting, clean composition, no text, no logos, photorealistic."
)


def _generate_dalle_image(client: OpenAI, prompt: str, attempt: int = 0) -> bytes:
    use_prompt = prompt if attempt == 0 else SAFE_FALLBACK_PROMPT
    try:
        resp = client.images.generate(
            model=IMAGE_MODEL,
            prompt=use_prompt,
            size=IMAGE_SIZE,
            quality=IMAGE_QUALITY,
            output_format="webp",
            n=1,
        )
        return base64.b64decode(resp.data[0].b64_json)
    except Exception as exc:
        msg = str(exc).lower()
        if any(t in msg for t in ["safety", "policy", "content filter", "violat"]) and attempt == 0:
            print("[image_actions] Safety rejection; retrying with fallback prompt")
            return _generate_dalle_image(client, prompt, attempt=1)
        raise


def generate_article_image(article: dict) -> dict:
    prompt = article.get("image_prompt", "")
    slug = article.get("slug", "unknown")

    if not prompt:
        title = article.get("title", "")
        prompt = f"Dramatic editorial photo representing: {title}. Photorealistic, no text, no logos."

    client = _openai_client()
    last_exc: Exception | None = None
    for attempt in range(2):
        try:
            image_bytes = _generate_dalle_image(client, prompt)
            break
        except Exception as exc:
            last_exc = exc
            if attempt == 0:
                time.sleep(3)
    else:
        raise last_exc  # type: ignore[misc]

    filename = f"{uuid.uuid4()}.webp"
    s3_key = f"posts/{filename}"
    _s3.put_object(Bucket=BUCKET, Key=s3_key, Body=image_bytes, ContentType="image/webp")
    print(f"[image_actions] Article image → s3://{BUCKET}/{s3_key}")
    return {"s3_key": s3_key, "filename": filename, "hugo_image_path": f"img/posts/{filename}"}


# ---------------------------------------------------------------------------
# Social image generation (PIL overlay)
# ---------------------------------------------------------------------------
TARGET_SIZE = 1080


def _load_article_image_from_s3(s3_key: str) -> Image.Image:
    obj = _s3.get_object(Bucket=BUCKET, Key=s3_key)
    return Image.open(BytesIO(obj["Body"].read())).convert("RGBA")


def _fit_and_crop(img: Image.Image, target: int = TARGET_SIZE) -> Image.Image:
    min_fill_h = int(target * 2 / 3)
    orig_w, orig_h = img.size
    scale = max(target / max(orig_w, 1), min_fill_h / max(orig_h, 1))
    new_w, new_h = int(orig_w * scale), int(orig_h * scale)
    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    if new_w > target:
        left = (new_w - target) // 2
        img = img.crop((left, 0, left + target, new_h))
    if new_h > target:
        img = img.crop((0, 0, target, target))
    elif new_h < target:
        canvas = Image.new("RGBA", (target, target), (0, 0, 0, 255))
        canvas.paste(img, (0, 0))
        img = canvas
    return img


def _apply_gradient(img: Image.Image) -> Image.Image:
    w, h = img.size
    gradient = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(gradient)
    start_y = int(h / 3)
    for y in range(start_y, h):
        alpha = int(255 * (y - start_y) / max(h - start_y, 1) * 2)
        draw.line([(0, y), (w, y)], fill=(0, 0, 0, min(alpha, 255)))
    return Image.alpha_composite(img, gradient)


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in [
        "/opt/fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont,
               max_width: int) -> list[str]:
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def generate_social_image(article: dict, article_image_s3_key: str) -> dict:
    title = article.get("title", "")
    slug = article.get("slug", "unknown")

    img = _load_article_image_from_s3(article_image_s3_key)
    img = _fit_and_crop(img)
    img = _apply_gradient(img)

    width, height = img.size
    draw = ImageDraw.Draw(img)
    padding = 60
    max_text_width = width - padding * 2
    max_text_height = height // 2 - padding

    font_size = 64
    font = _load_font(font_size)
    lines = _wrap_text(draw, title, font, max_text_width)
    line_spacing = int(font_size * 0.2)
    text_height = (
        sum(draw.textbbox((0, 0), l, font=font)[3] for l in lines)
        + line_spacing * max(len(lines) - 1, 0)
    )

    while text_height > max_text_height and font_size > 32:
        font_size -= 4
        font = _load_font(font_size)
        lines = _wrap_text(draw, title, font, max_text_width)
        line_spacing = int(font_size * 0.2)
        text_height = (
            sum(draw.textbbox((0, 0), l, font=font)[3] for l in lines)
            + line_spacing * max(len(lines) - 1, 0)
        )

    text_y = max(0, height - 20 - text_height)

    if LOGO_PATH.exists():
        try:
            logo = Image.open(LOGO_PATH).convert("RGBA")
            max_logo_h = 150
            scale = min(1.0, max_logo_h / max(logo.height, 1))
            logo = logo.resize(
                (int(logo.width * scale), int(logo.height * scale)), Image.Resampling.LANCZOS
            )
            logo_x = (width - logo.width) // 2
            logo_y = max(0, text_y - logo.height - 20)
            img.alpha_composite(logo, (logo_x, logo_y))
            bar_y = logo_y + logo.height // 2 - 2
            bar_thickness = 5
            if logo_x - 20 > 40:
                draw.rectangle([40, bar_y, logo_x - 20, bar_y + bar_thickness], fill=(255, 255, 255, 255))
            if logo_x + logo.width + 20 < width - 40:
                draw.rectangle([logo_x + logo.width + 20, bar_y, width - 40, bar_y + bar_thickness],
                               fill=(255, 255, 255, 255))
        except Exception as exc:
            print(f"[image_actions] Logo overlay failed (non-fatal): {exc}")

    y = text_y
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        x = (width - bbox[2]) // 2
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
        y += (bbox[3] - bbox[1]) + line_spacing

    border = 20
    bordered = Image.new("RGBA", (width + border * 2, height + border * 2), (255, 255, 255, 255))
    bordered.paste(img, (border, border))

    buf = BytesIO()
    bordered.convert("RGB").save(buf, "WEBP", quality=85)
    buf.seek(0)
    filename = f"social-{uuid.uuid4()}.webp"
    s3_key = f"social/{filename}"
    _s3.put_object(Bucket=BUCKET, Key=s3_key, Body=buf.getvalue(), ContentType="image/webp")
    print(f"[image_actions] Social image → s3://{BUCKET}/{s3_key}")
    return {"s3_key": s3_key, "filename": filename}


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
    inputs = _flow_inputs(event)
    # Detect action from input shape
    if "article_image_s3_key" in inputs:
        print(f"[image_actions] Action: generate_social_image")
        article = inputs["article"]
        s3_key = inputs["article_image_s3_key"]
        try:
            return generate_social_image(article, s3_key)
        except Exception as exc:
            print(f"[image_actions] Social image failed (non-fatal): {exc}")
            return {"s3_key": "", "filename": "", "error": str(exc), "skipped": True}
    else:
        print(f"[image_actions] Action: generate_article_image")
        article = inputs.get("article", inputs)
        try:
            return generate_article_image(article)
        except Exception as exc:
            print(f"[image_actions] Article image failed: {exc}")
            raise
