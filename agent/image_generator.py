"""
AI image generation module using OpenAI DALL-E
"""

import logging
from pathlib import Path
import uuid
import requests
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
            # Generate image with DALL-E
            response = self.client.images.generate(
                model=self.config.OPENAI_IMAGE_MODEL,
                prompt=prompt,
                size=self.config.IMAGE_SIZE,
                quality=self.config.IMAGE_QUALITY,
                n=1,
            )
            
            # Get image URL
            image_url = response.data[0].url
            
            # Download and save image
            image_filename = f"{uuid.uuid4()}.webp"
            image_path = self.output_dir / image_filename
            
            self._download_image(image_url, image_path)
            
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
            
            img = Image.open(article_image_path)
            
            # Resize for Instagram (1080x1080 for feed, 1080x1920 for story)
            img = img.resize((1080, 1080), Image.Resampling.LANCZOS)
            
            # Create drawing context
            draw = ImageDraw.Draw(img)
            
            # TODO: Add text overlay with article title
            # This requires proper font handling
            # For now, save without overlay
            
            # Save social media version
            social_filename = f"social-{uuid.uuid4()}.webp"
            social_path = self.config.HUGO_STATIC_DIR / 'img' / 'posts' / social_filename
            
            img.save(social_path, 'WEBP', quality=85)
            
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
