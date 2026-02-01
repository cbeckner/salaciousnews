# Salacious News Content Agent

Automated content generation pipeline for Salacious News.

## Overview

This agent automates the entire content creation workflow:

1. **Fetch News** - Scrapes recent news articles from various sources
2. **Rewrite Content** - Uses OpenAI GPT-4 to rewrite articles in sensationalist style
3. **Generate Images** - Creates AI images using DALL-E 3 based on article content
4. **Publish to Hugo** - Creates properly formatted markdown files in Hugo content structure
5. **Social Media** - Creates and publishes promotional posts with images

## Setup

### 1. Install Dependencies

```bash
cd agent
pip install -r requirements.txt
```

Or use a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment file and add your API keys:

```bash
cp .env.example .env
```

Edit `.env` and add:
- **Required**: `OPENAI_API_KEY` - Get from https://platform.openai.com/
- **Optional**: `NEWS_API_KEY` - Get from https://newsapi.org/
- **Optional**: Instagram credentials for social media posting

### 3. Run the Agent

```bash
python main.py
```

This will:
- Fetch 3 recent news articles
- Rewrite them in Salacious News style
- Generate AI images for each
- Create Hugo markdown files
- Post one article to social media

## Module Overview

### `main.py`
Entry point and pipeline orchestration. Run this to execute the full workflow.

### `config.py`
Configuration management - loads settings from environment variables and defines paths.

### `news_fetcher.py`
Fetches news articles from various sources:
- News API integration (TODO)
- RSS feed parsing (TODO)
- Direct web scraping with BeautifulSoup

### `content_generator.py`
OpenAI GPT-4 integration for:
- Rewriting articles in clickbait/sensationalist style
- Generating image prompts for DALL-E
- Creating social media captions
- Auto-categorization and tagging

### `image_generator.py`
DALL-E 3 integration for:
- Generating article featured images
- Creating social media promotional images
- Image post-processing and optimization

### `hugo_publisher.py`
Creates Hugo-compatible markdown files with proper:
- Frontmatter formatting (matching existing site structure)
- Category placement
- Image path references
- Date formatting

### `social_media.py`
Publishes content to social media platforms:
- Instagram (via Graph API)
- Twitter/X (TODO)
- Facebook (TODO)

## Usage Examples

### Generate 5 articles instead of 3

```python
from main import ContentAgent

agent = ContentAgent()
agent.run(num_articles=5)
```

### Test individual modules

```python
from news_fetcher import NewsFetcher
from config import Config

config = Config()
fetcher = NewsFetcher(config)
articles = fetcher.fetch_articles(1)
print(articles)
```

## Configuration Options

See `.env.example` for all available configuration options.

Key settings:
- `OPENAI_MODEL` - GPT model to use (default: gpt-4-turbo-preview)
- `IMAGE_SIZE` - DALL-E image dimensions (default: 1792x1024)
- `IMAGE_QUALITY` - 'standard' or 'hd' (default: standard)

## Development Status

### ✅ Implemented
- Module structure and framework
- Configuration management
- Hugo publisher (markdown generation)
- OpenAI integration scaffolding

### 🚧 TODO
- News API integration
- RSS feed parsing
- Web scraping implementation
- Auto-categorization logic
- Tag generation
- Social media API integration
- Error handling and retries
- Logging improvements
- Unit tests

## Troubleshooting

### ModuleNotFoundError
Make sure you've installed dependencies:
```bash
pip install -r requirements.txt
```

### API Key Errors
Verify your `.env` file has `OPENAI_API_KEY` set correctly.

### Image Generation Fails
- Check you have sufficient OpenAI API credits
- Verify image prompts don't violate content policies

## Contributing

When adding new features:
1. Update the relevant module
2. Add configuration options to `config.py` and `.env.example`
3. Update this README
4. Test with `python main.py`

## License

Part of the Salacious News project.
