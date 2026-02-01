"""
OpenAI-powered content generation module
"""

import json
from typing import Dict
from openai import OpenAI
from logging_config import get_logger

logger = get_logger(__name__)

# Proven prompts from previous implementation (safety-tuned)
TONE_SALACIOUS = (
    "You are a stylist at an upscale salon. Customers come to you for all the latest news and you love to gossip. "
    "Keep the tone playful and dramatic while avoiding graphic, hateful, or explicit content."
)

GET_CONTENT_SALACIOUS = """Summarize the article in a salacious, gossip-forward tone using more than 300 words but fewer than 700 words.
Keep it newsy and non-graphic: avoid explicit sexual content, graphic violence, hate speech, or self-harm details; use neutral, high-level phrasing.
Return the summarized article along with an associated Clickbait headline and between one to five keywords.
Categorize the article as one of the following: Business, Entertainment, Other, Politics, Sports, Technology, US, World.
Format the results as a JSON object with the fields: ClickbaitHeadline, Summary, Keywords (array), Category."""


class ContentGenerator:
    """Generates article content and image prompts using OpenAI"""
    
    def __init__(self, config):
        self.config = config
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
    
    def generate_article(self, source_article: Dict) -> Dict:
        """
        Rewrite article in sensationalist/clickbait style and generate image prompt
        
        Args:
            source_article: Dictionary with 'title', 'content', 'url', 'source', etc.
            
        Returns:
            Dictionary with:
            - title: Rewritten clickbait title
            - description: Meta description
            - content: Rewritten article content
            - image_prompt: Prompt for image generation
            - tags: List of relevant tags
            - category: Article category
            - slug: URL-friendly slug
            - source: Original source
            - original_url: Original article URL
        """
        logger.debug(f"Generating content for: {source_article.get('title', 'Unknown')}")
        
        # Generate rewritten content (with safety resilience)
        rewritten = self._rewrite_article(source_article)
        
        # Generate image prompt
        image_prompt = self._generate_image_prompt(rewritten['title'], rewritten['content'])
        
        # Tags and category come from the rewrite response
        tags = rewritten.get('keywords', [])
        category = self._validate_category(rewritten.get('category', 'Other'))
        
        # Generate slug
        slug = self._generate_slug(rewritten['title'])
        
        return {
            'title': rewritten['title'],
            'description': rewritten['description'],
            'content': rewritten['content'],
            'image_prompt': image_prompt,
            'tags': tags,
            'category': category,
            'slug': slug,
            'source': source_article.get('source', 'Unknown'),
            'original_url': source_article.get('url', ''),
        }
    
    def _rewrite_article(self, source_article: Dict) -> Dict:
        """
        Rewrite article in Salacious News style using proven prompts
        
        Returns:
            Dict with 'title', 'description', 'content', 'category', 'keywords'
        """
        # Build the full article content for context
        article_content = f"""
Title: {source_article.get('title', '')}
Source: {source_article.get('source', 'Unknown')}
URL: {source_article.get('url', '')}

Content:
{source_article.get('content', '')[:3000]}
"""
        
        prompt = f"""{GET_CONTENT_SALACIOUS}

Original article:
{article_content}

Important: Ensure the Summary field includes the {{{{< articlead >}}}} shortcode after approximately the 2nd paragraph."""

        try:
            response = self.client.chat.completions.create(
                model=self.config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": TONE_SALACIOUS},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )

            result = response.choices[0].message.content
            return self._parse_json_response(result)

        except Exception as e:
            if self._is_safety_error(e):
                logger.warning("Safety system flagged content generation; using fallback summary.")
                return self._fallback_summary(source_article)
            logger.error(f"Error rewriting article: {e}")
            raise
    
    def _parse_json_response(self, response: str) -> Dict:
        """
        Parse the JSON response from OpenAI
        
        Expected format:
        {
            "ClickbaitHeadline": "...",
            "Summary": "...",
            "Keywords": [...],
            "Category": "..."
        }
        """
        try:
            data = json.loads(response)
            
            # Extract description from first sentence or two of summary
            summary = data.get('Summary', '')
            description = summary.split('.')[0] + '.' if '.' in summary else summary[:150]
            
            return {
                'title': data.get('ClickbaitHeadline', ''),
                'description': description,
                'content': summary,
                'keywords': data.get('Keywords', []),
                'category': data.get('Category', 'Other')
            }
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response: {e}")
            logger.error(f"Response was: {response}")
            # Return fallback
            return {
                'title': 'Breaking News',
                'description': 'Read the latest updates',
                'content': response,
                'keywords': [],
                'category': 'Other'
            }
    
    def _generate_image_prompt(self, title: str, content: str) -> str:
        """Generate a DALL-E image prompt based on article content"""
        prompt = f"""Based on this article, create a detailed, safe image prompt for a news thumbnail:

Title: {title}
Content: {content[:500]}

Requirements:
- Photorealistic or cinematic editorial style
- Eye-catching but non-graphic
- Avoid explicit violence, gore, sexual content, hate, or self-harm imagery
- No text, logos, or identifiable private individuals

Provide only the image prompt, nothing else."""

        try:
            response = self.client.chat.completions.create(
                model=self.config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert at creating safe, policy-compliant image prompts."},
                    {"role": "user", "content": prompt}
                ]
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            if self._is_safety_error(e):
                logger.warning("Safety system flagged image prompt; using safe fallback.")
                return "A neutral newsroom scene with journalists at desks, soft lighting, no text, no logos."
            logger.error(f"Error generating image prompt: {e}")
            return "A dramatic news scene"

    def _fallback_summary(self, source_article: Dict) -> Dict:
        """Fallback summary if safety system blocks generation"""
        raw = (source_article.get("content") or "").strip()
        sentences = [s.strip() for s in raw.replace("\n", " ").split(".") if s.strip()]
        summary = ". ".join(sentences[:8]).strip()
        if summary:
            summary = summary + "."
        else:
            summary = "A developing story with limited publicly available details."
        summary = summary + "\n\n{{< articlead >}}\n\n"
        summary = summary + "More updates will follow as official sources provide additional details."

        return {
            "title": "Breaking Update: Authorities Release New Details",
            "description": summary.split(".")[0] + ".",
            "content": summary,
            "keywords": [],
            "category": "Other",
        }

    def _is_safety_error(self, error: Exception) -> bool:
        message = str(error).lower()
        return any(token in message for token in ["safety", "policy", "content filter", "violat"])
    
    def _validate_category(self, category: str) -> str:
        """Validate category against allowed list"""
        valid_categories = ['Business', 'Entertainment', 'Other', 'Politics', 
                           'Sports', 'Technology', 'US', 'World']
        
        # Check if category is valid
        if category in valid_categories:
            return category
        
        # Try case-insensitive match
        for valid in valid_categories:
            if category.lower() == valid.lower():
                return valid
        
        # Default to Other
        logger.warning(f"Invalid category '{category}', defaulting to 'Other'")
        return 'Other'
    
    def _generate_slug(self, title: str) -> str:
        """Generate URL-friendly slug from title"""
        import re
        import uuid
        
        # Convert to lowercase and replace spaces with hyphens
        slug = title.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '-', slug)
        slug = slug.strip('-')
        
        # Add random 5-char hex suffix
        suffix = uuid.uuid4().hex[:5]
        slug = f"{slug[:50]}-{suffix}"
        
        return slug
    
    def generate_social_post(self, article: Dict) -> str:
        """
        Generate social media caption for article promotion
        
        Args:
            article: Article dictionary
            
        Returns:
            Social media caption text
        """
        prompt = f"""Create a short, engaging Instagram caption to promote this article:

Title: {article['title']}
Content preview: {article['content'][:200]}

The caption should:
- Be 1-2 sentences
- Create curiosity
- Include relevant emoji
- End with a call to action (link in bio, swipe up, etc.)
- Be under 150 characters
- Include relevant hashtags (not included in character count)

Provide only the caption text."""

        try:
            response = self.client.chat.completions.create(
                model=self.config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a social media expert."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating social post: {e}")
            return f"🔥 Breaking news! Check out our latest story. Link in bio! #SalaciousNews"
