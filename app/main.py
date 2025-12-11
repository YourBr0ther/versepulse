#!/usr/bin/env python3
"""VersePulse - Star Citizen Patch Notes Monitor

Monitors RSI Spectrum for new patch notes and sends Pushbullet notifications.
"""

import os
import sys
import time
import logging
import schedule
from dotenv import load_dotenv

from app.database import init_db, is_post_seen, mark_post_seen, get_seen_count
from app.scraper import scrape_forum_threads, scrape_post_content
from app.summarizer import summarize_patch, ensure_model_available, wait_for_ollama
from app.notifier import send_notification, test_notification

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("versepulse")

CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "10"))


def check_for_new_posts():
    """Check for new patch notes and send notifications."""
    logger.info("Checking for new patch notes...")

    try:
        posts = scrape_forum_threads()

        if not posts:
            logger.warning("No posts found")
            return

        new_count = 0
        for post in posts:
            if is_post_seen(post.post_id):
                continue

            logger.info(f"New post found: {post.title}")
            new_count += 1

            # Get full content
            content = scrape_post_content(post)
            post.content = content

            # Generate summary
            summary = summarize_patch(post.title, post.content)

            # Send notification
            success = send_notification(
                title=post.title,
                summary=summary.summary,
                features=summary.features,
                url=post.url
            )

            if success:
                mark_post_seen(post.post_id, post.title, post.url)
                logger.info(f"Notification sent for: {post.title}")
            else:
                logger.error(f"Failed to send notification for: {post.title}")

        if new_count == 0:
            logger.info("No new posts found")
        else:
            logger.info(f"Processed {new_count} new post(s)")

    except Exception as e:
        logger.error(f"Error checking for new posts: {e}", exc_info=True)


def startup():
    """Initialize the application."""
    logger.info("=" * 50)
    logger.info("VersePulse - Star Citizen Patch Notes Monitor")
    logger.info("=" * 50)

    # Check required config
    if not os.getenv("PUSHBULLET_API_KEY"):
        logger.error("PUSHBULLET_API_KEY environment variable is required")
        sys.exit(1)

    # Initialize database
    logger.info("Initializing database...")
    init_db()
    logger.info(f"Database initialized. Seen posts: {get_seen_count()}")

    # Wait for Ollama
    logger.info("Waiting for Ollama to be available...")
    if not wait_for_ollama(max_retries=30, retry_delay=10):
        logger.error("Ollama is not available. Exiting.")
        sys.exit(1)

    # Ensure model is available
    logger.info("Ensuring model is available...")
    if not ensure_model_available():
        logger.error("Could not ensure model availability. Exiting.")
        sys.exit(1)

    logger.info(f"Check interval: {CHECK_INTERVAL} minutes")
    logger.info("Startup complete!")


def main():
    """Main entry point."""
    startup()

    # Run initial check
    logger.info("Running initial check...")
    check_for_new_posts()

    # Schedule periodic checks
    schedule.every(CHECK_INTERVAL).minutes.do(check_for_new_posts)

    logger.info(f"Scheduler started. Checking every {CHECK_INTERVAL} minutes.")
    logger.info("Press Ctrl+C to stop.")

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
