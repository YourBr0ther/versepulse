"""Spectrum forum scraper using Playwright."""

import os
import re
import logging
from dataclasses import dataclass
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)

FORUM_URL = os.getenv(
    "FORUM_URL",
    "https://robertsspaceindustries.com/spectrum/community/SC/forum/190048"
)


@dataclass
class PatchPost:
    """Represents a patch notes post."""
    post_id: str
    title: str
    url: str
    content: str = ""


def scrape_forum_threads() -> list[PatchPost]:
    """Scrape the Spectrum forum for patch note threads."""
    posts = []
    seen_ids = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York"
        )
        page = context.new_page()

        try:
            logger.info(f"Loading forum page: {FORUM_URL}")
            page.goto(FORUM_URL, wait_until="networkidle", timeout=60000)

            # Wait for forum threads to load
            page.wait_for_selector("a[href*='/thread/']", timeout=30000)

            # Give extra time for dynamic content
            page.wait_for_timeout(3000)

            # Find all thread links
            links = page.query_selector_all("a[href*='/forum/190048/thread/']")
            logger.info(f"Found {len(links)} thread links")

            for link in links:
                href = link.get_attribute("href")
                title = link.inner_text().strip()

                # Skip empty titles or non-thread links
                if not href or not title or len(title) < 5:
                    continue

                # Extract thread slug from URL (e.g., "star-citizen-alpha-4-5-ptu-patch-notes-7")
                # URL format: /spectrum/community/SC/forum/190048/thread/SLUG
                match = re.search(r'/thread/([^/]+?)(?:/\d+)?$', href)
                if match:
                    post_slug = match.group(1)

                    # Skip if we've already seen this thread
                    if post_slug in seen_ids:
                        continue
                    seen_ids.add(post_slug)

                    full_url = f"https://robertsspaceindustries.com{href}" if href.startswith("/") else href

                    posts.append(PatchPost(
                        post_id=post_slug,
                        title=title,
                        url=full_url
                    ))

                    # Limit to first 10 unique posts
                    if len(posts) >= 10:
                        break

        except PlaywrightTimeout:
            logger.error("Timeout waiting for forum page to load")
        except Exception as e:
            logger.error(f"Error scraping forum: {e}")
        finally:
            browser.close()

    logger.info(f"Found {len(posts)} unique posts")
    return posts


def scrape_post_content(post: PatchPost) -> str:
    """Scrape the full content of a patch notes post."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York"
        )
        page = context.new_page()

        try:
            logger.info(f"Loading post: {post.url}")
            page.goto(post.url, wait_until="networkidle", timeout=60000)

            # Wait longer for JavaScript to fully render
            page.wait_for_timeout(8000)

            # Try multiple selectors for post content (ordered by specificity)
            content_selectors = [
                "[class*='rich-text']",
                "[class*='RichText']",
                "[class*='thread-body']",
                "[class*='message-body']",
                "[class*='post-body']",
                ".content-main",
                "article",
            ]

            content = ""
            for selector in content_selectors:
                elements = page.query_selector_all(selector)
                if elements:
                    # Get text from first substantial content element
                    for el in elements:
                        text = el.inner_text()
                        if len(text) > 200:  # Ensure meaningful content
                            content = text
                            logger.info(f"Found content using selector: {selector} ({len(content)} chars)")
                            break
                    if content:
                        break

            if not content or len(content) < 200:
                # Fallback: get all text from the page body
                logger.info("Using body fallback for content")
                content = page.inner_text("body")

            # Clean up content - limit to first 8000 chars for LLM processing
            content = content.strip()[:8000]

            return content

        except PlaywrightTimeout:
            logger.error(f"Timeout loading post: {post.url}")
            return ""
        except Exception as e:
            logger.error(f"Error scraping post content: {e}")
            return ""
        finally:
            browser.close()


def get_latest_posts(limit: int = 5) -> list[PatchPost]:
    """Get the latest posts with their content."""
    posts = scrape_forum_threads()[:limit]

    for post in posts:
        post.content = scrape_post_content(post)

    return posts
