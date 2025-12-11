"""SQLite database for tracking seen patch notes."""

import sqlite3
import os
from pathlib import Path


DB_PATH = Path(os.getenv("DB_PATH", "/app/data/versepulse.db"))


def init_db() -> None:
    """Initialize the database and create tables if they don't exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS seen_posts (
            post_id TEXT PRIMARY KEY,
            title TEXT,
            url TEXT,
            seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def is_post_seen(post_id: str) -> bool:
    """Check if a post has already been seen."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT 1 FROM seen_posts WHERE post_id = ?", (post_id,))
    result = cursor.fetchone() is not None

    conn.close()
    return result


def mark_post_seen(post_id: str, title: str, url: str) -> None:
    """Mark a post as seen."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT OR IGNORE INTO seen_posts (post_id, title, url) VALUES (?, ?, ?)",
        (post_id, title, url)
    )

    conn.commit()
    conn.close()


def get_seen_count() -> int:
    """Get the total number of seen posts."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM seen_posts")
    count = cursor.fetchone()[0]

    conn.close()
    return count
