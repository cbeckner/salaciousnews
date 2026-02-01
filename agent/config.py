"""
Configuration management for the content agent
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Configuration settings for the content agent"""
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-5')
    OPENAI_IMAGE_MODEL = os.getenv('OPENAI_IMAGE_MODEL', 'chatgpt-image-latest')
    
    # News Sources
    NEWS_SOURCES = os.getenv('NEWS_SOURCES', 'cnn,bbc,reuters').split(',')
    NEWS_API_KEY = os.getenv('NEWS_API_KEY')
    
    # Content Settings
    CATEGORIES = [
        'Business', 'Entertainment', 'Other', 
        'Politics', 'Sports', 'Technology', 'US', 'World'
    ]
    
    # Hugo Settings
    HUGO_CONTENT_DIR = Path(__file__).parent.parent / 'content'
    HUGO_STATIC_DIR = Path(__file__).parent.parent / 'static'
    
    # Image Settings
    IMAGE_SIZE = os.getenv('IMAGE_SIZE', '1536x1024')  
    IMAGE_QUALITY = os.getenv('IMAGE_QUALITY', 'standard')  # or 'hd'
    
    # Social Media Settings
    INSTAGRAM_ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN')
    INSTAGRAM_USER_ID = os.getenv('INSTAGRAM_USER_ID')
    SITE_BASE_URL = os.getenv('SITE_BASE_URL', 'https://salacious.news/')

    # GitHub Actions monitoring
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
    GITHUB_REPO = os.getenv('GITHUB_REPO')  # e.g. "owner/repo"
    GITHUB_BRANCH = os.getenv('GITHUB_BRANCH', 'main')
    
    # Content Generation Settings
    ARTICLE_MIN_LENGTH = int(os.getenv('ARTICLE_MIN_LENGTH', '300'))
    
    @classmethod
    def validate(cls):
        """Validate that required configuration is present"""
        required = ['OPENAI_API_KEY']
        missing = [key for key in required if not getattr(cls, key)]
        
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
        
        return True
