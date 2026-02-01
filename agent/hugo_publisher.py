"""
Hugo content publishing module
"""

from pathlib import Path
from datetime import datetime
from typing import Dict
from logging_config import get_logger

logger = get_logger(__name__)


class HugoPublisher:
    """Publishes generated content to Hugo"""
    
    def __init__(self, config):
        self.config = config
        self.content_dir = config.HUGO_CONTENT_DIR
    
    def publish_article(self, article: Dict) -> Path:
        """
        Create Hugo markdown file for article
        
        Args:
            article: Dictionary with article data
            
        Returns:
            Path to created markdown file
        """
        logger.debug(f"Publishing article: {article['title']}")
        
        # Create category directory if needed
        category_dir = self.content_dir / article['category']
        category_dir.mkdir(parents=True, exist_ok=True)
        
        # Create markdown file
        filename = f"{article['slug']}.md"
        file_path = category_dir / filename
        
        # Generate frontmatter and content
        content = self._generate_markdown(article)
        
        # Write file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.debug(f"Article published to: {file_path}")
        return file_path
    
    def _generate_markdown(self, article: Dict) -> str:
        """
        Generate complete markdown file with frontmatter
        
        Args:
            article: Article dictionary
            
        Returns:
            Complete markdown content
        """
        # Format date in Hugo format
        date = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.0000000Z')
        
        # Build frontmatter
        frontmatter = f"""---
Title: "{article['title']}"
Description: "{article.get('description', '')}"
Date: {date}
Categories:
- {article['category']}
Tags:
{self._format_tags(article.get('tags', []))}
Featured: true
Thumbnail:
  Src: ./{article['image_path'].split('/')[-1]}
  Visibility:
  - post
ImagePrompt: "{article['image_prompt']}"
Source: {article['source']}
OriginalUrl: {article['original_url']}

---
"""
        
        # Combine frontmatter and content
        return frontmatter + article['content']
    
    def _format_tags(self, tags: list) -> str:
        """Format tags list for YAML frontmatter"""
        if not tags:
            return ''
        return '\n'.join([f'- {tag}' for tag in tags])