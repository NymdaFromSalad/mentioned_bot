import aiosqlite
from typing import List, Optional, Tuple
import sqlite3
import os

_DB_PATH: str = "mentions.sqlite3"


def set_db_path(path: str) -> None:
    global _DB_PATH
    _DB_PATH = path


async def init_db() -> None:
    # The bot is now still in testing, db will be removed BY THE USER, when schema changes

    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS mention_counts (
                chat_id INTEGER NOT NULL,
                target_user_id INTEGER,
                target_username TEXT,
                target_display TEXT,
                identity TEXT,
                count INTEGER NOT NULL DEFAULT 0,
                UNIQUE(chat_id, identity)
            )
            """
        )
        await db.commit()


async def increment_mention(chat_id: int, user_id: Optional[int], username: Optional[str], display: str) -> None:
    norm_username = username.lower() if username else None
    identity: Optional[str] = None
    if user_id is not None:
        identity = f"id:{user_id}"
    elif norm_username is not None:
        identity = f"username:{norm_username}"

    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO mention_counts (chat_id, target_user_id, target_username, target_display, count, identity)
            VALUES (?, ?, ?, ?, 1, ?)
            ON CONFLICT(chat_id, identity)
            DO UPDATE SET count = count + 1,
                          target_display = excluded.target_display
            """,
            (chat_id, user_id, norm_username, display, identity),
        )
        await db.commit()


async def get_stats(chat_id: int) -> List[Tuple[str, int]]:
    async with aiosqlite.connect(_DB_PATH) as db:
        async with db.execute(
            """
            SELECT COALESCE(target_display, CASE WHEN target_username IS NOT NULL THEN '@' || lower(target_username) ELSE 'Неизвестно' END) AS name,
                   count
            FROM mention_counts
            WHERE chat_id = ?
            ORDER BY count DESC, name ASC
            LIMIT 50
            """,
            (chat_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [(row[0], row[1]) for row in rows]
