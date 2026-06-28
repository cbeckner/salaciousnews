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
ACCENT_RED = (227, 30, 30, 255)
WHITE = (255, 255, 255, 255)


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
    Black gradient that fades in from 46% down and is fully opaque by 64%.
    This gives a solid dark band covering the bottom ~36% for the badge,
    title, and footer branding.
    """
    w, h = img.size
    gradient = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(gradient)
    fade_start = int(h * 0.46)   # gradient begins here
    fade_end   = int(h * 0.64)   # fully black from here down
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
    category = (article.get("category") or "").strip()
    slug = article.get("slug", "unknown")

    # Defense-in-depth: strip em/en-dashes — the bundled font may render them as
    # missing-glyph boxes on some Lambda deploys. The title source should already
    # avoid these, but normalize here too in case one slips through.
    title = title.replace("—", ":").replace("–", ":").replace("  ", " ").strip().upper()

    img = _load_article_image_from_s3(article_image_s3_key)
    img = _fit_and_crop(img)
    img = _apply_gradient(img)

    width, height = img.size
    draw = ImageDraw.Draw(img)
    padding = 48
    max_text_width = width - padding * 2

    # Target zone: the solid-black band at the bottom (below gradient fade-end at 64%)
    text_zone_top    = int(height * 0.64)   # aligns with gradient full-black point
    text_zone_bottom = height - 28          # small bottom margin

    # --- "NEWS" badge with flanking divider lines ----------------------------
    badge_font = _load_font(34)
    badge_text = "HOT GOSSIP"
    badge_bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    badge_pad_x, badge_pad_y = 26, 14
    badge_w = (badge_bbox[2] - badge_bbox[0]) + badge_pad_x * 2
    badge_h = (badge_bbox[3] - badge_bbox[1]) + badge_pad_y * 2
    badge_x = (width - badge_w) // 2
    badge_y = text_zone_top + 26

    divider_y = badge_y + badge_h // 2
    divider_thickness = 4
    if badge_x - 24 > padding:
        draw.rectangle([padding, divider_y, badge_x - 24, divider_y + divider_thickness],
                       fill=(255, 255, 255, 220))
    if badge_x + badge_w + 24 < width - padding:
        draw.rectangle([badge_x + badge_w + 24, divider_y, width - padding, divider_y + divider_thickness],
                       fill=(255, 255, 255, 220))

    draw.rounded_rectangle(
        [badge_x, badge_y, badge_x + badge_w, badge_y + badge_h],
        radius=10, fill=ACCENT_RED,
    )
    draw.text(
        (badge_x + badge_pad_x - badge_bbox[0], badge_y + badge_pad_y - badge_bbox[1]),
        badge_text, font=badge_font, fill=WHITE,
    )

    # --- Footer brand line -----------------------------------------------------
    footer_font = _load_font(28)
    footer_text = f"SALACIOUS.NEWS | {category.upper()}" if category else "SALACIOUS.NEWS"
    footer_bbox = draw.textbbox((0, 0), footer_text, font=footer_font)
    footer_h = footer_bbox[3] - footer_bbox[1]

    # --- Title block: fills the space between badge and footer -----------------
    title_top = badge_y + badge_h + 28
    title_bottom = text_zone_bottom - footer_h - 24
    max_text_height = max(0, title_bottom - title_top)

    # Start large and shrink until text fits. Min 48px so it's always readable.
    def _measure(fs: int) -> tuple[list[str], int, int]:
        f = _load_font(fs)
        ls = int(fs * 0.22)
        wrapped = _wrap_text(draw, title, f, max_text_width)
        th = (
            sum(draw.textbbox((0, 0), l, font=f)[3] for l in wrapped)
            + ls * max(len(wrapped) - 1, 0)
        )
        return wrapped, th, ls

    font_size = 110
    lines, text_height, line_spacing = _measure(font_size)
    while text_height > max_text_height and font_size > 48:
        font_size -= 4
        lines, text_height, line_spacing = _measure(font_size)
    font = _load_font(font_size)

    # Vertically center the title block between the badge and the footer
    text_y = title_top + max(0, (max_text_height - text_height) // 2)

    # Punchy two-tone treatment: lead line in accent red, rest in white
    y = text_y
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        x = (width - bbox[2]) // 2
        color = ACCENT_RED if i == 0 else WHITE
        draw.text((x, y), line, font=font, fill=color)
        y += (bbox[3] - bbox[1]) + line_spacing

    # Draw the footer brand line, centered at the bottom of the dark band
    footer_x = (width - (footer_bbox[2] - footer_bbox[0])) // 2
    footer_y = text_zone_bottom - footer_h
    draw.text((footer_x - footer_bbox[0], footer_y - footer_bbox[1]), footer_text,
              font=footer_font, fill=ACCENT_RED)

    border = 20
    bordered = Image.new("RGBA", (width + border * 2, height + border * 2), (255, 255, 255, 255))
    bordered.paste(img, (border, border))

    buf = BytesIO()
    bordered.convert("RGB").save(buf, "JPEG", quality=90)
    buf.seek(0)
    filename = f"social-{uuid.uuid4()}.jpg"
    s3_key = f"social/{filename}"
    _s3.put_object(Bucket=BUCKET, Key=s3_key, Body=buf.getvalue(), ContentType="image/jpeg")
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
