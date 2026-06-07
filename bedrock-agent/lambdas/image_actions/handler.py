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
    """
    Black gradient that fades in from 55% down and is fully opaque by 72%.
    This gives a solid dark zone covering the bottom ~28% for the text.
    """
    w, h = img.size
    gradient = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(gradient)
    fade_start = int(h * 0.55)   # gradient begins here
    fade_end   = int(h * 0.72)   # fully black from here down
    for y in range(fade_start, h):
        if y < fade_end:
            alpha = int(255 * (y - fade_start) / max(fade_end - fade_start, 1))
        else:
            alpha = 255
        draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))
    return Image.alpha_composite(img, gradient)


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    # NotoSans-Bold first — full Unicode coverage including em-dash, curly quotes, etc.
    # Roboto-Bold as secondary (good Latin coverage, may miss some Unicode).
    here = Path(__file__).parent
    candidates = [
        here / "NotoSans-Bold.ttf",
        here / "Roboto-Bold.ttf",
        Path("/opt/fonts/NotoSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
        Path("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(str(path), size)
        except Exception:
            pass
    # Last resort: Pillow built-in scalable font (10.1+)
    try:
        return ImageFont.load_default(size=size)  # type: ignore[call-arg]
    except TypeError:
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

    # Normalise punctuation for clean word-wrapping.
    # Add spaces around em-dash so it's treated as a separate token by _wrap_text.
    title = title.replace("—", " — ").replace("  ", " ").strip()

    img = _load_article_image_from_s3(article_image_s3_key)
    img = _fit_and_crop(img)
    img = _apply_gradient(img)

    width, height = img.size
    draw = ImageDraw.Draw(img)
    padding = 48
    max_text_width = width - padding * 2

    # Target zone: the solid-black band at the bottom (below gradient fade-end at 72%)
    text_zone_top    = int(height * 0.72)   # aligns with gradient full-black point
    text_zone_bottom = height - 28          # small bottom margin
    max_text_height  = text_zone_bottom - text_zone_top

    # Start large and shrink until text fits. Min 52px so it's always readable.
    def _measure(fs: int) -> tuple[list[str], int, int]:
        f = _load_font(fs)
        ls = int(fs * 0.28)
        wrapped = _wrap_text(draw, title, f, max_text_width)
        th = (
            sum(draw.textbbox((0, 0), l, font=f)[3] for l in wrapped)
            + ls * max(len(wrapped) - 1, 0)
        )
        return wrapped, th, ls

    font_size = 120
    lines, text_height, line_spacing = _measure(font_size)
    while text_height > max_text_height and font_size > 52:
        font_size -= 4
        lines, text_height, line_spacing = _measure(font_size)
    font = _load_font(font_size)

    # Vertically center the text block within the dark zone
    text_y = text_zone_top + max(0, (max_text_height - text_height) // 2)

    # Logo sits in the gradient transition zone, centered, with horizontal bars
    if LOGO_PATH.exists():
        try:
            logo = Image.open(LOGO_PATH).convert("RGBA")
            max_logo_h = 100  # slightly smaller so it doesn't crowd the text
            scale = min(1.0, max_logo_h / max(logo.height, 1))
            logo = logo.resize(
                (int(logo.width * scale), int(logo.height * scale)), Image.Resampling.LANCZOS
            )
            logo_x = (width - logo.width) // 2
            # Place logo in the gradient zone, just above the solid-black text band
            logo_y = max(0, text_zone_top - logo.height - 12)
            img.alpha_composite(logo, (logo_x, logo_y))
            bar_y = logo_y + logo.height // 2 - 2
            bar_thickness = 4
            if logo_x - 20 > 40:
                draw.rectangle([40, bar_y, logo_x - 20, bar_y + bar_thickness], fill=(255, 255, 255, 200))
            if logo_x + logo.width + 20 < width - 40:
                draw.rectangle([logo_x + logo.width + 20, bar_y, width - 40, bar_y + bar_thickness],
                               fill=(255, 255, 255, 200))
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
