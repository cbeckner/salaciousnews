#!/usr/bin/env python3
"""
Quick test harness for social media image generation.

Usage:
  python test_social_image.py --image-path img/posts/your-image.webp --title "Your Title"
  python test_social_image.py --image-path /absolute/path/to/image.webp --title "Your Title"
"""

import argparse
import shutil
from pathlib import Path

from config import Config
from image_generator import ImageGenerator


def _normalize_image_path(image_path: str, static_dir: Path) -> str:
    path = Path(image_path)

    if path.is_absolute():
        try:
            relative = path.relative_to(static_dir)
            return str(relative.as_posix())
        except ValueError:
            # Copy into static/img/posts
            dest_dir = static_dir / "img" / "posts"
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_path = dest_dir / path.name
            if not dest_path.exists():
                shutil.copy(path, dest_path)
            return str(dest_path.relative_to(static_dir).as_posix())

    # Relative path provided
    return image_path.lstrip("./")


def main():
    parser = argparse.ArgumentParser(description="Test social media image generation")
    parser.add_argument("--image-path", required=True, help="Path to image (relative to static/ or absolute)")
    parser.add_argument("--title", required=True, help="Article title to overlay")
    args = parser.parse_args()

    config = Config()
    generator = ImageGenerator(config)

    relative_path = _normalize_image_path(args.image_path, config.HUGO_STATIC_DIR)

    article = {
        "title": args.title,
        "image_path": relative_path,
    }

    output = generator.generate_social_image(article)
    print(f"Social image generated: {output}")


if __name__ == "__main__":
    main()
