#!/usr/bin/env python3
"""
Salacious News Content Generation Agent

Main entry point for automated content pipeline:
1. Fetch recent news articles
2. Rewrite articles and generate image prompts
3. Generate AI images for articles
4. Create social media promotion
5. Publish content
"""

import logging
from typing import List
from pathlib import Path

from config import Config
from news_fetcher import NewsFetcher
from content_generator import ContentGenerator
from image_generator import ImageGenerator
from hugo_publisher import HugoPublisher
from social_media import SocialMediaPublisher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ContentAgent:
    """Orchestrates the content generation pipeline"""
    
    def __init__(self):
        self.config = Config()
        self.news_fetcher = NewsFetcher(self.config)
        self.content_generator = ContentGenerator(self.config)
        self.image_generator = ImageGenerator(self.config)
        self.hugo_publisher = HugoPublisher(self.config)
        self.social_media = SocialMediaPublisher(self.config)
    
    def run(self, num_articles: int = 3):
        """
        Execute the full content generation pipeline
        
        Args:
            num_articles: Number of articles to generate (default: 3)
        """
        logger.info(f"Starting content generation pipeline for {num_articles} articles")
        
        try:
            # Step 1: Fetch news articles
            logger.info("Step 1: Fetching recent news articles...")
            articles = self.news_fetcher.fetch_articles(num_articles)
            logger.info(f"Fetched {len(articles)} articles")
            
            # Step 2: Generate content for each article
            logger.info("Step 2: Generating rewritten content and image prompts...")
            generated_articles = []
            for article in articles:
                generated = self.content_generator.generate_article(article)
                generated_articles.append(generated)
            logger.info(f"Generated content for {len(generated_articles)} articles")
            
            # Step 3: Generate images for each article
            logger.info("Step 3: Generating AI images...")
            for article in generated_articles:
                image_path = self.image_generator.generate_image(
                    prompt=article['image_prompt'],
                    article_slug=article['slug']
                )
                article['image_path'] = image_path
            logger.info(f"Generated {len(generated_articles)} images")
            
            # Step 4: Publish to Hugo
            logger.info("Step 4: Publishing articles to Hugo...")
            published_files = []
            for article in generated_articles:
                file_path = self.hugo_publisher.publish_article(article)
                published_files.append(file_path)
            logger.info(f"Published {len(published_files)} articles")
            
            # Step 5: Create and publish social media promotion
            logger.info("Step 5: Creating social media promotion...")
            featured_article = generated_articles[0]  # Promote the first article
            social_image = self.image_generator.generate_social_image(featured_article)
            social_post = self.content_generator.generate_social_post(featured_article)
            
            self.social_media.publish(
                image_path=social_image,
                caption=social_post,
                article_url=featured_article['url']
            )
            logger.info("Social media post published successfully")
            
            logger.info("Content generation pipeline completed successfully!")
            return published_files
            
        except Exception as e:
            logger.error(f"Error in content pipeline: {e}", exc_info=True)
            raise


def main():
    """Main entry point"""
    agent = ContentAgent()
    agent.run(num_articles=3)


if __name__ == "__main__":
    main()
