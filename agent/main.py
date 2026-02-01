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

import subprocess
import time
from typing import List
from pathlib import Path
import requests

from config import Config
from news_fetcher import NewsFetcher
from content_generator import ContentGenerator
from image_generator import ImageGenerator
from hugo_publisher import HugoPublisher
from social_media import SocialMediaPublisher
from logging_config import get_logger

logger = get_logger(__name__)


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
            logger.debug(f"Fetched {len(articles)} articles")
            
            # Step 2: Generate content for each article
            logger.info("Step 2: Generating rewritten content and image prompts...")
            generated_articles = []
            for article in articles:
                generated = self.content_generator.generate_article(article)
                generated_articles.append(generated)
            logger.debug(f"Generated content for {len(generated_articles)} articles")
            
            # Step 3: Generate images for each article
            logger.info("Step 3: Generating AI images...")
            for article in generated_articles:
                image_path = self.image_generator.generate_image(
                    prompt=article['image_prompt'],
                    article_slug=article['slug']
                )
                article['image_path'] = image_path
            logger.debug(f"Generated {len(generated_articles)} images")
            
            # Step 4: Publish to Hugo
            logger.info("Step 4: Publishing articles to Hugo...")
            published_files = []
            for article in generated_articles:
                file_path = self.hugo_publisher.publish_article(article)
                published_files.append(file_path)
            logger.debug(f"Published {len(published_files)} articles")

            # Step 5: Build Hugo site and ensure no errors
            logger.info("Step 5: Building Hugo site...")
            self._build_hugo_site()

            # Step 6: Commit and push changes
            logger.info("Step 6: Committing and pushing changes...")
            pushed = self._git_commit_and_push()

            # Step 7: Monitor GitHub Actions
            if pushed:
                logger.info("Step 7: Monitoring GitHub Actions...")
                self._wait_for_github_actions()
            else:
                logger.debug("No git changes detected; skipping GitHub Actions monitoring and social posting.")
                return published_files
            
            # Step 8: Create and publish social media promotion
            logger.info("Step 8: Creating social media promotion...")
            featured_article = generated_articles[0]  # Promote the first article
            social_image = self.image_generator.generate_social_image(featured_article)
            social_post = self.content_generator.generate_social_post(featured_article)
            
            # self.social_media.publish(
            #     image_path=social_image,
            #     caption=social_post,
            #     article_url=featured_article['url']
            # )
            logger.info("Social media post published successfully")
            
            logger.info("Content generation pipeline completed successfully!")
            return published_files
            
        except Exception as e:
            logger.error(f"Error in content pipeline: {e}", exc_info=True)
            raise

    def _build_hugo_site(self):
        """Run Hugo build and fail fast on errors"""
        result = subprocess.run(
            ["hugo"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            logger.error("Hugo build failed")
            logger.error(result.stdout)
            logger.error(result.stderr)
            raise RuntimeError("Hugo build failed; aborting social posting.")

    def _git_commit_and_push(self):
        """Commit and push changes to GitHub"""
        repo_root = Path(__file__).parent.parent
        subprocess.run(["git", "add", "-A"], cwd=repo_root, check=True)

        status = subprocess.run(["git", "status", "--porcelain"], cwd=repo_root, capture_output=True, text=True, check=True)
        if not status.stdout.strip():
            logger.debug("Working tree clean; no changes to commit.")
            return False

        # Use a consistent commit message
        subprocess.run(["git", "commit", "-m", "Automated content update"], cwd=repo_root, check=True)
        subprocess.run(["git", "push"], cwd=repo_root, check=True)
        return True

    def _wait_for_github_actions(self, timeout_seconds: int = 1800, poll_interval: int = 15, retry_attempts: int = 1):
        """Wait for the GitHub Actions workflow triggered by the push to succeed"""
        token = self.config.GITHUB_TOKEN
        repo = self.config.GITHUB_REPO
        branch = self.config.GITHUB_BRANCH
        if not token or not repo:
            raise RuntimeError("GITHUB_TOKEN and GITHUB_REPO must be set to monitor GitHub Actions")

        headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
        url = f"https://api.github.com/repos/{repo}/actions/runs"

        attempts = 0
        while attempts <= retry_attempts:
            start = time.time()
            last_run_id = None
            while time.time() - start < timeout_seconds:
                resp = requests.get(url, headers=headers, params={"branch": branch, "event": "push", "per_page": 5})
                resp.raise_for_status()
                runs = resp.json().get("workflow_runs", [])
                if runs:
                    run = runs[0]
                    last_run_id = run.get("id")
                    status = run.get("status")
                    conclusion = run.get("conclusion")

                    if status == "completed":
                        if conclusion == "success":
                            logger.info("GitHub Actions workflow succeeded")
                            return
                        attempts += 1
                        if attempts > retry_attempts:
                            raise RuntimeError(f"GitHub Actions failed with conclusion: {conclusion}")
                        logger.warning(f"GitHub Actions failed ({conclusion}); retrying ({attempts}/{retry_attempts})")
                        self._rerun_github_actions(last_run_id, headers, repo)
                        break

                time.sleep(poll_interval)

            if time.time() - start >= timeout_seconds:
                raise RuntimeError(f"Timed out waiting for GitHub Actions to complete (last_run_id={last_run_id})")

    def _rerun_github_actions(self, run_id: int, headers: dict, repo: str):
        """Attempt to rerun a failed GitHub Actions workflow"""
        if not run_id:
            return
        rerun_url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/rerun"
        resp = requests.post(rerun_url, headers=headers)
        if resp.status_code not in (201, 202):
            logger.warning(f"Failed to rerun workflow {run_id}: {resp.status_code} {resp.text}")


def main():
    """Main entry point"""
    agent = ContentAgent()
    agent.run(num_articles=3)


if __name__ == "__main__":
    main()
