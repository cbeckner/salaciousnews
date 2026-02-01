"""
Social media publishing module
"""

from pathlib import Path
from typing import Optional
import requests
from logging_config import get_logger

logger = get_logger(__name__)


class SocialMediaPublisher:
    """Publishes content to social media platforms"""
    
    def __init__(self, config):
        self.config = config
        self.instagram_token = config.INSTAGRAM_ACCESS_TOKEN
        self.instagram_user_id = config.INSTAGRAM_USER_ID
    
    def publish(self, image_path: str, caption: str, article_url: str):
        """
        Publish post to social media
        
        Args:
            image_path: Path to social media image
            caption: Post caption/text
            article_url: URL to article
        """
        logger.debug("Publishing to social media...")
        
        # Add article URL to caption
        full_caption = f"{caption}\n\nRead more: {article_url}\n\n#SalaciousNews #BreakingNews"
        
        # Publish to Instagram
        if self.instagram_token:
            self._publish_to_instagram(image_path, full_caption)
        else:
            logger.warning("Instagram credentials not configured, skipping Instagram post")
        
        # TODO: Add other platforms (Twitter/X, Facebook, etc.)
    
    def _publish_to_instagram(self, image_path: str, caption: str):
        """
        Publish to Instagram using Graph API
        
        Note: Requires Instagram Business Account and Facebook Page
        See: https://developers.facebook.com/docs/instagram-api/guides/content-publishing
        """
        logger.debug("Publishing to Instagram...")
        
        try:
            # Step 1: Create media container
            container_url = f"https://graph.facebook.com/v18.0/{self.instagram_user_id}/media"
            
            container_params = {
                'image_url': self._upload_to_public_url(image_path),
                'caption': caption,
                'access_token': self.instagram_token
            }
            
            container_response = requests.post(container_url, data=container_params)
            container_response.raise_for_status()
            container_id = container_response.json()['id']
            
            # Step 2: Publish media container
            publish_url = f"https://graph.facebook.com/v18.0/{self.instagram_user_id}/media_publish"
            
            publish_params = {
                'creation_id': container_id,
                'access_token': self.instagram_token
            }
            
            publish_response = requests.post(publish_url, data=publish_params)
            publish_response.raise_for_status()
            
            logger.debug("Successfully published to Instagram")
            
        except Exception as e:
            logger.error(f"Error publishing to Instagram: {e}")
            raise
    
    def _upload_to_public_url(self, image_path: str) -> str:
        """
        Upload image to publicly accessible URL
        
        Instagram API requires a public URL for the image.
        Options:
        1. Upload to S3 and return URL
        2. Use existing static site image URL
        3. Use temporary image hosting service
        
        Args:
            image_path: Local path to image
            
        Returns:
            Public URL to image
        """
        # Social images are saved under assets/img/social and served at /img/social/
        base_url = (self.config.SITE_BASE_URL or "").rstrip("/")
        filename = Path(image_path).name
        return f"{base_url}/img/social/{filename}"
    
    def _publish_to_twitter(self, image_path: str, caption: str):
        """
        Publish to Twitter/X
        
        Note: Requires Twitter API credentials
        """
        # TODO: Implement Twitter publishing using tweepy or similar
        logger.debug("Twitter publishing not yet implemented")
        pass
    
    def _publish_to_facebook(self, image_path: str, caption: str):
        """
        Publish to Facebook
        
        Note: Requires Facebook API credentials
        """
        # TODO: Implement Facebook publishing
        logger.debug("Facebook publishing not yet implemented")
        pass
