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

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            logger.info(f"Loading forum page: {FORUM_URL}")
            page.goto(FORUM_URL, wait_until="networkidle", timeout=60000)

            # Wait for forum threads to load
            page.wait_for_selector(".forum-thread-item, .thread-subject, [class*='thread']", timeout=30000)

            # Give extra time for dynamic content
            page.wait_for_timeout(3000)

            # Try multiple selector patterns for thread items
            thread_selectors = [
                ".forum-thread-item",
                "[class*='thread-item']",
                "[class*='ThreadItem']",
                ".thread-row",
                "a[href*='/thread/']"
            ]

            threads = []
            for selector in thread_selectors:
                threads = page.query_selector_all(selector)
                if threads:
                    logger.info(f"Found {len(threads)} threads using selector: {selector}")
                    break

            if not threads:
                # Fallback: find all links containing /thread/
                links = page.query_selector_all("a[href*='/forum/190048/thread/']")
                logger.info(f"Fallback: found {len(links)} thread links")

                for link in links[:10]:  # Limit to first 10
                    href = link.get_attribute("href")
                    title = link.inner_text().strip()

                    if href and title:
                        # Extract post ID from URL
                        match = re.search(r'/thread/(\d+)', href)
                        if match:
                            post_id = match.group(1)
                            full_url = f"https://robertsspaceindustries.com{href}" if href.startswith("/") else href

                            posts.append(PatchPost(
                                post_id=post_id,
                                title=title,
                                url=full_url
                            ))
            else:
                for thread in threads[:10]:  # Limit to first 10
                    try:
                        # Try to find the link within the thread item
                        link = thread.query_selector("a[href*='/thread/']")
                        if not link:
                            link = thread if thread.get_attribute("href") else None

                        if link:
                            href = link.get_attribute("href")
                            title = link.inner_text().strip()

                            if href:
                                match = re.search(r'/thread/(\d+)', href)
                                if match:
                                    post_id = match.group(1)
                                    full_url = f"https://robertsspaceindustries.com{href}" if href.startswith("/") else href

                                    posts.append(PatchPost(
                                        post_id=post_id,
                                        title=title or f"Post {post_id}",
                                        url=full_url
                                    ))
                    except Exception as e:
                        logger.warning(f"Error parsing thread: {e}")
                        continue

        except PlaywrightTimeout:
            logger.error("Timeout waiting for forum page to load")
        except Exception as e:
            logger.error(f"Error scraping forum: {e}")
        finally:
            browser.close()

    logger.info(f"Found {len(posts)} posts")
    return posts


def scrape_post_content(post: PatchPost) -> str:
    """Scrape the full content of a patch notes post."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            logger.info(f"Loading post: {post.url}")
            page.goto(post.url, wait_until="networkidle", timeout=60000)

            # Wait for content to load
            page.wait_for_selector(".content-main, .thread-content, [class*='content']", timeout=30000)
            page.wait_for_timeout(2000)

            # Try multiple selectors for post content
            content_selectors = [
                ".thread-content .content-main",
                ".message-content",
                ".post-content",
                "[class*='ThreadContent']",
                ".content-main",
                "article"
            ]

            content = ""
            for selector in content_selectors:
                elements = page.query_selector_all(selector)
                if elements:
                    # Get text from first main content element
                    content = elements[0].inner_text()
                    if len(content) > 100:  # Ensure we got meaningful content
                        logger.info(f"Found content using selector: {selector}")
                        break

            if not content:
                # Fallback: get all text from the page body
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
