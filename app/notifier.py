"""Pushbullet notification integration."""

import os
import logging
import requests

logger = logging.getLogger(__name__)

PUSHBULLET_API_KEY = os.getenv("PUSHBULLET_API_KEY", "")
PUSHBULLET_API_URL = "https://api.pushbullet.com/v2/pushes"


def send_notification(title: str, summary: str, features: list[str], url: str) -> bool:
    """Send a Pushbullet notification with patch summary."""
    if not PUSHBULLET_API_KEY:
        logger.error("PUSHBULLET_API_KEY not set")
        return False

    # Build the message body
    body_parts = [summary, ""]

    if features:
        body_parts.append("New Features:")
        for feature in features[:10]:  # Limit to 10 features
            body_parts.append(f"• {feature}")
        body_parts.append("")

    body_parts.append(f"Read more: {url}")

    body = "\n".join(body_parts)

    try:
        response = requests.post(
            PUSHBULLET_API_URL,
            headers={
                "Access-Token": PUSHBULLET_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "type": "note",
                "title": f"🚀 {title}",
                "body": body
            },
            timeout=30
        )

        if response.status_code == 200:
            logger.info(f"Notification sent: {title}")
            return True
        else:
            logger.error(f"Pushbullet API error: {response.status_code} - {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        logger.error("Cannot connect to Pushbullet API")
        return False
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        return False


def test_notification() -> bool:
    """Send a test notification to verify setup."""
    return send_notification(
        title="VersePulse Test",
        summary="VersePulse is configured and working!",
        features=["Test notification successful"],
        url="https://robertsspaceindustries.com/spectrum/community/SC/forum/190048"
    )
