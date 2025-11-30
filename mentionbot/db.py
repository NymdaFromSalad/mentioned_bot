import aiosqlite
from typing import List, Optional, Tuple

_DB_PATH: str = "mentions.sqlite3"


def set_db_path(path: str) -> None:
    global _DB_PATH
    _DB_PATH = path


async def init_db() -> None:
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS mention_counts (
                chat_id INTEGER NOT NULL,
                target_user_id INTEGER,
                target_username TEXT,
                target_display TEXT,
                count INTEGER NOT NULL DEFAULT 0,
                UNIQUE(chat_id, target_user_id, target_username)
            )
            """
        )
        await db.commit()


async def increment_mention(chat_id: int, user_id: Optional[int], username: Optional[str], display: str) -> None:
    norm_username = username.lower() if username else None
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO mention_counts (chat_id, target_user_id, target_username, target_display, count)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(chat_id, target_user_id, target_username)
            DO UPDATE SET count = count + 1,
                          target_display = excluded.target_display
            """,
            (chat_id, user_id, norm_username, display),
        )
        await db.commit()


async def get_stats(chat_id: int) -> List[Tuple[str, int]]:
    async with aiosqlite.connect(_DB_PATH) as db:
        async with db.execute(
            """
            SELECT COALESCE(target_display, CASE WHEN target_username IS NOT NULL THEN '@' || target_username ELSE 'Unknown' END) AS name,
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
