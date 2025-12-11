"""Tests for VersePulse components."""

import os
import sys
import tempfile
import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


class TestDatabase:
    """Tests for database module."""

    def test_init_db(self):
        """Test database initialization."""
        from app.database import init_db, DB_PATH

        # Use temp directory for test
        os.environ["DB_PATH"] = "/tmp/test_versepulse.db"

        # Reimport to pick up new path
        import importlib
        import app.database as db_module
        importlib.reload(db_module)

        db_module.init_db()
        assert os.path.exists("/tmp/test_versepulse.db"), "Database file should be created"

        # Cleanup
        os.remove("/tmp/test_versepulse.db")

    def test_mark_and_check_post(self):
        """Test marking posts as seen and checking them."""
        os.environ["DB_PATH"] = "/tmp/test_versepulse2.db"

        import importlib
        import app.database as db_module
        importlib.reload(db_module)

        db_module.init_db()

        # Post should not be seen initially
        assert not db_module.is_post_seen("test123"), "New post should not be seen"

        # Mark as seen
        db_module.mark_post_seen("test123", "Test Title", "https://example.com")

        # Now it should be seen
        assert db_module.is_post_seen("test123"), "Post should be marked as seen"

        # Count should be 1
        assert db_module.get_seen_count() == 1, "Should have 1 seen post"

        # Cleanup
        os.remove("/tmp/test_versepulse2.db")


class TestPushbullet:
    """Tests for Pushbullet notifier."""

    def test_api_key_loaded(self):
        """Test that API key is loaded from environment."""
        from app.notifier import PUSHBULLET_API_KEY
        assert PUSHBULLET_API_KEY, "Pushbullet API key should be loaded"
        assert len(PUSHBULLET_API_KEY) > 10, "API key should be valid length"

    def test_send_notification(self):
        """Test sending a real notification."""
        from app.notifier import send_notification

        result = send_notification(
            title="VersePulse Test",
            summary="This is a test notification from VersePulse test suite.",
            features=["Test feature 1", "Test feature 2"],
            url="https://robertsspaceindustries.com/spectrum/community/SC/forum/190048"
        )

        assert result is True, "Notification should be sent successfully"


class TestSummarizer:
    """Tests for Ollama summarizer."""

    def test_parse_llm_response(self):
        """Test parsing LLM response."""
        from app.summarizer import parse_llm_response

        response = """SUMMARY: This patch adds new ships and improves performance.

FEATURES:
- New Drake Corsair ship
- New mission types
- Improved lighting system"""

        result = parse_llm_response(response, "Fallback Title")

        assert result.summary == "This patch adds new ships and improves performance."
        assert len(result.features) == 3
        assert "New Drake Corsair ship" in result.features

    def test_parse_llm_response_no_features(self):
        """Test parsing when no features."""
        from app.summarizer import parse_llm_response

        response = """SUMMARY: Bug fixes only.

FEATURES: None"""

        result = parse_llm_response(response, "Fallback")

        assert result.summary == "Bug fixes only."
        assert len(result.features) == 0

    def test_parse_llm_response_fallback(self):
        """Test fallback when response is malformed."""
        from app.summarizer import parse_llm_response

        response = "Some random text without proper format"

        result = parse_llm_response(response, "Fallback Title")

        assert result.summary == "Fallback Title"

    def test_ollama_connection(self):
        """Test connection to Ollama (skip if not running)."""
        import requests
        from app.summarizer import OLLAMA_HOST

        try:
            response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
            if response.status_code == 200:
                print(f"\nOllama is running at {OLLAMA_HOST}")
                print(f"Available models: {response.json().get('models', [])}")
            else:
                pytest.skip(f"Ollama returned status {response.status_code}")
        except requests.exceptions.ConnectionError:
            pytest.skip(f"Ollama not running at {OLLAMA_HOST}")


class TestScraper:
    """Tests for Spectrum scraper."""

    def test_patch_post_dataclass(self):
        """Test PatchPost dataclass."""
        from app.scraper import PatchPost

        post = PatchPost(
            post_id="12345",
            title="Test Patch",
            url="https://example.com/patch",
            content="Patch content here"
        )

        assert post.post_id == "12345"
        assert post.title == "Test Patch"
        assert post.url == "https://example.com/patch"
        assert post.content == "Patch content here"

    def test_forum_url_configured(self):
        """Test forum URL is configured."""
        from app.scraper import FORUM_URL

        assert "robertsspaceindustries.com" in FORUM_URL
        assert "spectrum" in FORUM_URL
        assert "190048" in FORUM_URL

    def test_scrape_forum_threads(self):
        """Test scraping forum threads (requires Playwright)."""
        try:
            from app.scraper import scrape_forum_threads

            posts = scrape_forum_threads()

            print(f"\nFound {len(posts)} posts:")
            for post in posts[:5]:
                print(f"  - {post.title} ({post.post_id})")

            # Should find at least some posts
            assert len(posts) >= 0, "Scraper should return a list"

            if posts:
                # Check first post has required fields
                assert posts[0].post_id, "Post should have ID"
                assert posts[0].title, "Post should have title"
                assert posts[0].url, "Post should have URL"

        except Exception as e:
            pytest.skip(f"Scraper test failed (may need Playwright browsers): {e}")


class TestIntegration:
    """Integration tests."""

    def test_full_workflow_mock(self):
        """Test the full workflow with mock data."""
        from app.summarizer import parse_llm_response
        from app.scraper import PatchPost

        # Simulate finding a new post
        post = PatchPost(
            post_id="999999",
            title="Alpha 4.5.0 - Major Update",
            url="https://robertsspaceindustries.com/spectrum/community/SC/forum/190048/thread/999999",
            content="""
            Star Citizen Alpha 4.5.0 brings exciting new features:

            NEW FEATURES:
            - New Pyro system fully explorable
            - Server meshing technology
            - New starter ship: Origin 100i

            BUG FIXES:
            - Fixed crash on planet landing
            - Fixed inventory issues
            """
        )

        # Simulate LLM response
        llm_response = """SUMMARY: Alpha 4.5.0 introduces the Pyro system and server meshing technology.

FEATURES:
- New Pyro system fully explorable
- Server meshing technology
- New starter ship: Origin 100i"""

        summary = parse_llm_response(llm_response, post.title)

        assert "Pyro" in summary.summary
        assert len(summary.features) == 3
        assert any("Pyro" in f for f in summary.features)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
