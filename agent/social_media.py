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
    
    def _validate_instagram_credentials(self) -> bool:
        """Return True if Instagram credentials look real, log a warning and return False otherwise."""
        placeholders = {"your_instagram_user_id", "your_access_token", ""}
        if not self.instagram_token or self.instagram_token.lower() in placeholders:
            logger.warning("INSTAGRAM_ACCESS_TOKEN is not configured; skipping Instagram post")
            return False
        if not self.instagram_user_id or self.instagram_user_id.lower() in placeholders:
            logger.warning("INSTAGRAM_USER_ID is not configured; skipping Instagram post")
            return False
        return True

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
        if self._validate_instagram_credentials():
            self._publish_to_instagram(image_path, full_caption)
        
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
            if not container_response.ok:
                logger.error(f"Instagram media creation failed ({container_response.status_code}): {container_response.text}")
                container_response.raise_for_status()
            container_id = container_response.json()['id']
            
            # Step 2: Publish media container
            publish_url = f"https://graph.facebook.com/v25.0/{self.instagram_user_id}/media_publish"
            
            publish_params = {
                'creation_id': container_id,
                'access_token': self.instagram_token
            }
            
            publish_response = requests.post(publish_url, data=publish_params)
            if not publish_response.ok:
                logger.error(f"Instagram publish failed ({publish_response.status_code}): {publish_response.text}")
                publish_response.raise_for_status()
            
            logger.info(f"Successfully published to Instagram (post id: {publish_response.json().get('id')})")
            
        except requests.HTTPError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error publishing to Instagram: {e}")
            raise
    
    def _upload_to_public_url(self, image_path: str) -> str:
        """
        Return the public URL for a social image that has been saved under static/img/social/.

        Instagram API requires a public URL for the image.

        Args:
            image_path: Local path to image

        Returns:
            Public URL to image
        """
        # Social images are saved under static/img/social/ and served at /img/social/
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
