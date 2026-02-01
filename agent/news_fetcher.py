"""
News article fetching and parsing module
"""

import hashlib
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from logging_config import get_logger

logger = get_logger(__name__)


class NewsFetcher:
    """Fetches and parses news articles from various sources"""
    
    def __init__(self, config):
        self.config = config
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def fetch_articles(self, num_articles: int = 5) -> List[Dict]:
        """
        Fetch recent news articles
        
        Args:
            num_articles: Number of articles to fetch
            
        Returns:
            List of article dictionaries with keys:
            - title: Original article title
            - content: Article text content
            - url: Source URL
            - source: Source name (e.g., 'CNN')
            - published_date: Publication date
            - category: Suggested category
        """
        logger.debug(f"Fetching {num_articles} news articles...")
        
        # Step 1: fetch headlines from NewsAPI across categories
        headlines = self._fetch_headlines_newsapi()
        if not headlines:
            logger.warning("No headlines retrieved from NewsAPI")
            return []

        # Step 2: rank/select 3-5 candidates using OpenAI
        target = max(3, min(5, num_articles))
        selected_ids = self._rank_headlines_with_openai(headlines, target)

        selected = [h for h in headlines if h["id"] in selected_ids]

        articles: List[Dict[str, Any]] = []
        for item in selected:
            parsed = self._parse_article_content(item["url"])
            if not parsed:
                continue
            content = parsed.get("content", "").strip()
            if len(content) < self.config.ARTICLE_MIN_LENGTH:
                continue
            articles.append({
                "title": item["title"],
                "content": content,
                "url": item["url"],
                "source": item.get("source", "Unknown"),
                "published_date": item.get("published_at"),
                "category": item.get("category", "Other"),
            })
            if len(articles) >= num_articles:
                break
        
        return articles

    def _fetch_headlines_newsapi(self) -> List[Dict[str, Any]]:
        """Fetch top headlines for each category via NewsAPI"""
        api_key = getattr(self.config, "NEWS_API_KEY", None)
        if not api_key:
            logger.error("NEWS_API_KEY is not configured; cannot fetch headlines")
            return []
        
        # Map internal categories to NewsAPI categories
        category_map = {
            "Business": "business",
            "Entertainment": "entertainment",
            "Sports": "sports",
            "Technology": "technology",
            "Health": "health",
            "Science": "science",
            "General": "general"
        }

        headlines: List[Dict[str, Any]] = []
        seen_urls = set()

        for cat in self.config.CATEGORIES:
            api_cat = category_map.get(cat, "general")
            url = "https://newsapi.org/v2/top-headlines"
            params = {
                "country": "us",
                "category": api_cat,
                "pageSize": 10,
                "apiKey": api_key,
            }
            try:
                resp = self.session.get(url, params=params, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                for idx, art in enumerate(data.get("articles", [])):
                    src_url = art.get("url")
                    if not src_url or src_url in seen_urls:
                        continue
                    seen_urls.add(src_url)
                    art_id = self._make_id(src_url)
                    headlines.append({
                        "id": art_id,
                        "title": art.get("title", ""),
                        "url": src_url,
                        "source": (art.get("source") or {}).get("name", ""),
                        "published_at": art.get("publishedAt"),
                        "category": cat,
                    })
            except Exception as e:
                logger.error(f"Error fetching headlines for category {cat}: {e}")

        return headlines

    def _rank_headlines_with_openai(self, headlines: List[Dict[str, Any]], target: int) -> List[str]:
        """Use OpenAI to pick 3-5 salacious candidates from headlines"""
        if not headlines:
            return []

        # Build prompt string in the format id>>headline:::...
        head_str = ":::".join([f"{h['id']}>>{h['title']}" for h in headlines if h.get('title')])
        prompt = (
            "You are a veteran journalist with a discerning eye for what the public wants to know. "
            "Pick between three and five interesting stories from the following headlines. "
            "Each selected headline should be about a completely different topic. "
            "Each headline is separated by ':::'. The id and the headline are separated by '>>'. "
            "Return the IDs of the selected stories in a comma separated list."
        )

        try:
            response = self.client.chat.completions.create(
                model=self.config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a veteran journalist who selects diverse, high-engagement stories."},
                    {"role": "user", "content": f"{prompt}\n\nHeadlines:\n{head_str}"}
                ]
            )
            raw = response.choices[0].message.content.strip()
            ids = [item.strip() for item in raw.replace("\n", ",").split(',') if item.strip()]
            # Keep at most target (and at least 3 if possible)
            ids = ids[:max(3, min(5, target))]
            return ids
        except Exception as e:
            logger.error(f"Error ranking headlines with OpenAI: {e}")
            # Fallback: first few headlines
            return [h['id'] for h in headlines[:target]]

    def _make_id(self, url: str) -> str:
        """Create a deterministic ID from the URL (NewsAPI article ids are null)"""
        return hashlib.md5(url.encode("utf-8")).hexdigest()[:12]
    
    def _parse_article_content(self, url: str) -> Dict:
        """
        Parse article content from URL
        
        Args:
            url: Article URL
            
        Returns:
            Dictionary with parsed article data
        """
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            # Remove script/style
            for tag in soup(['script', 'style', 'noscript']):
                tag.decompose()
            
            content = self._extract_paragraphs(soup)
            
            return {
                'title': soup.find('h1').get_text() if soup.find('h1') else '',
                'content': content,
                'url': url
            }
            
        except Exception as e:
            logger.error(f"Error parsing article {url}: {e}")
            return None
    
    def _extract_paragraphs(self, soup: BeautifulSoup) -> str:
        """Extract main content paragraphs from parsed HTML"""
        paragraphs = soup.find_all('p')
        content = '\n\n'.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
        return content

