"""
AI image generation module using OpenAI DALL-E
"""

import base64
import logging
from pathlib import Path
from unittest import result
import uuid
import requests
from typing import Dict
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


class ImageGenerator:
    """Generates images using OpenAI DALL-E"""
    
    def __init__(self, config):
        self.config = config
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.output_dir = config.HUGO_STATIC_DIR / 'img' / 'posts'
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_image(self, prompt: str, article_slug: str) -> str:
        """
        Generate an article featured image using DALL-E
        
        Args:
            prompt: Image generation prompt
            article_slug: Article slug for filename
            
        Returns:
            Relative path to generated image (e.g., 'img/posts/uuid.webp')
        """
        logger.info(f"Generating image for: {article_slug}")
        
        try:
            # Generate image 
            response = self.client.images.generate(
                model=self.config.OPENAI_IMAGE_MODEL,
                prompt=prompt,
                size=self.config.IMAGE_SIZE,
                quality=self.config.IMAGE_QUALITY,
                output_format="webp",
                n=1
            )

            image_filename = f"{uuid.uuid4()}.png"
            
            image_base64 = response.data[0].b64_json
            image_bytes = base64.b64decode(image_base64)

            image_path = self.output_dir / image_filename
            with open(image_path, "wb") as f:
                f.write(image_bytes)

            # # Get image URL
            # image_url = response.data[0].url
            
            # # Download and save image
            # image_path = self.output_dir / image_filename
            
            # self._download_image(image_url, image_path)
            
            logger.info(f"Image saved to: {image_path}")
            return f"img/posts/{image_filename}"
            
        except Exception as e:
            logger.error(f"Error generating image: {e}")
            raise
    
    def generate_social_image(self, article: Dict) -> str:
        """
        Generate a social media promotional image
        
        Args:
            article: Article dictionary with title and image_path
            
        Returns:
            Path to social media image
        """
        logger.info(f"Generating social media image for: {article['title']}")
        
        # Option 1: Generate a new image with DALL-E specifically for social
        # Option 2: Add text overlay to existing article image
        
        # For now, use Option 2 - overlay text on article image
        return self._create_text_overlay_image(article)
    
    def _create_text_overlay_image(self, article: Dict) -> str:
        """
        Create a social media image by overlaying text on the article image
        
        Args:
            article: Article dictionary
            
        Returns:
            Path to social media image
        """
        try:
            # Load the article image
            article_image_path = self.config.HUGO_STATIC_DIR / article['image_path']
            
            img = Image.open(article_image_path).convert("RGBA")
            
            # Resize without stretching; ensure image fills at least 2/3 height
            target_size = 1080
            min_fill_height = int(target_size * (2 / 3))
            orig_w, orig_h = img.size
            
            # Scale to target width or minimum height, preserving aspect ratio
            scale_w = target_size / max(1, orig_w)
            scale_h = min_fill_height / max(1, orig_h)
            scale = max(scale_w, scale_h)
            new_w = int(orig_w * scale)
            new_h = int(orig_h * scale)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            if new_w > target_size:
                # Crop horizontally to square, keep centered
                left = (new_w - target_size) // 2
                img = img.crop((left, 0, left + target_size, new_h))
                new_w = target_size
            
            if new_h > target_size:
                # Crop vertically to square, keep pinned to top
                img = img.crop((0, 0, target_size, target_size))
            elif new_h < target_size:
                # Pad on black background, pin to top
                canvas = Image.new("RGBA", (target_size, target_size), (0, 0, 0, 255))
                canvas.paste(img, (0, 0))
                img = canvas
            
            width, height = img.size
            
            # Add bottom gradient overlay (black to transparent)
            gradient = Image.new("RGBA", img.size, (0, 0, 0, 0))
            grad_draw = ImageDraw.Draw(gradient)
            start_fade = int(height * (1 / 3))
            end_fade = int(height * (2 / 3))
            print("Adding gradient from", start_fade, "to", end_fade)
            max_alpha = 255
            for y in range(start_fade, end_fade):
                alpha = int(abs(max_alpha * (y - start_fade) / (height - start_fade)) * 2)
                grad_draw.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))
            img = Image.alpha_composite(img, gradient)
            
            # Prepare text overlay
            draw = ImageDraw.Draw(img)
            title = article.get('title', '').strip()
            padding = 60
            max_text_width = width - (padding * 2)
            max_text_height = (height // 2) - padding
            
            # Load font (fallback to default)
            def load_font(size: int) -> ImageFont.FreeTypeFont:
                try:
                    return ImageFont.truetype("Arial.ttf", size)
                except Exception:
                    try:
                        return ImageFont.truetype("/Library/Fonts/Arial.ttf", size)
                    except Exception:
                        return ImageFont.load_default()
            
            def wrap_text(text: str, font: ImageFont.ImageFont, max_width: int) -> list:
                words = text.split()
                lines = []
                current = ""
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
            
            font_size = 64
            font = load_font(font_size)
            lines = wrap_text(title, font, max_text_width)
            line_spacing = int(font_size * 0.2)
            text_height = sum([draw.textbbox((0, 0), line, font=font)[3] for line in lines]) + (line_spacing * (len(lines) - 1))
            
            while text_height > max_text_height and font_size > 32:
                font_size -= 4
                font = load_font(font_size)
                lines = wrap_text(title, font, max_text_width)
                line_spacing = int(font_size * 0.2)
                text_height = sum([draw.textbbox((0, 0), line, font=font)[3] for line in lines]) + (line_spacing * (len(lines) - 1))
            
            # Position text aligned to bottom
            bottom_padding = 20
            text_y = max(0, height - bottom_padding - text_height)

            # Insert logo above text (centered, max height 75px)
            logo_path = self.config.HUGO_STATIC_DIR / "img" / "salacious-news-logo_clear.webp"
            if logo_path.exists():
                try:
                    logo = Image.open(logo_path).convert("RGBA")
                    max_logo_h = 150
                    scale = min(1.0, max_logo_h / max(1, logo.height))
                    logo_w = int(logo.width * scale)
                    logo_h = int(logo.height * scale)
                    logo = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
                    logo_x = (width - logo_w) // 2
                    logo_y = max(0, text_y - logo_h - 20)
                    img.alpha_composite(logo, (logo_x, logo_y))

                    # Add horizontal white bars next to the logo
                    bar_thickness = 5
                    bar_y = logo_y + (logo_h // 2) - (bar_thickness // 2)

                    left_bar_start = 40
                    left_bar_end = max(left_bar_start, logo_x - 20)
                    right_bar_start = min(width - 40, logo_x + logo_w + 20)
                    right_bar_end = width - 40

                    if left_bar_end > left_bar_start:
                        draw.rectangle(
                            [left_bar_start, bar_y, left_bar_end, bar_y + bar_thickness],
                            fill=(255, 255, 255, 255)
                        )

                    if right_bar_end > right_bar_start:
                        draw.rectangle(
                            [right_bar_start, bar_y, right_bar_end, bar_y + bar_thickness],
                            fill=(255, 255, 255, 255)
                        )
                except Exception as e:
                    logger.warning(f"Unable to add logo overlay: {e}")

            # Draw text lines
            y = text_y
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                line_width = bbox[2]
                x = (width - line_width) // 2
                draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
                y += (bbox[3] - bbox[1]) + line_spacing
            
            # Add border around image
            border_size = 20
            bordered = Image.new("RGBA", (width + border_size * 2, height + border_size * 2), (255, 255, 255, 255))
            bordered.paste(img, (border_size, border_size))
            img = bordered
            
            # Save social media version
            social_filename = f"social-{uuid.uuid4()}.webp"
            social_path = self.config.HUGO_STATIC_DIR / 'img' / 'posts' / social_filename
            
            img.convert("RGB").save(social_path, 'WEBP', quality=85)
            
            logger.info(f"Social image saved to: {social_path}")
            return str(social_path)
            
        except Exception as e:
            logger.error(f"Error creating social image: {e}")
            # Fallback: return original image path
            return str(self.config.HUGO_STATIC_DIR / article['image_path'])
    
    def _download_image(self, url: str, output_path: Path):
        """Download image from URL and save to file"""
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Save as WebP
        img = Image.open(requests.get(url, stream=True).raw)
        img.save(output_path, 'WEBP', quality=85)
