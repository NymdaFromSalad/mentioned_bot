import asyncio
import logging
import os
from typing import List, Optional, Tuple

from telegram import Update, MessageEntity
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

import aiosqlite

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

DB_PATH = os.getenv("MENTION_BOT_DB", "mentions.sqlite3")
TOKEN_ENV = "TELEGRAM_BOT_TOKEN"


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
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
 
 
async def _post_init(_: Application) -> None:
    # Ensure DB is initialized before handling updates
    await init_db()


def display_name_from_user(user) -> str:
    if user is None:
        return "Unknown"
    if user.username:
        return f"@{user.username}"
    name = user.first_name or ""
    if user.last_name:
        name = f"{name} {user.last_name}"
    return name.strip() or str(user.id)


async def increment_mention(chat_id: int, user_id: Optional[int], username: Optional[str], display: str) -> None:
    # Normalize username for storage (lowercase for uniqueness), but keep display as given
    norm_username = username.lower() if username else None
    async with aiosqlite.connect(DB_PATH) as db:
        # Upsert behavior with COALESCE on target fields
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
    async with aiosqlite.connect(DB_PATH) as db:
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


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Hi! I track how often people are mentioned in this chat.\n"
        "- Mention someone with @username or via text mention.\n"
        "- Use /stats to see the leaderboard.\n"
        "Stats are per chat and stored in SQLite."
    )
    await update.message.reply_text(text)


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not update.message:
        return
    chat_id = update.effective_chat.id
    stats = await get_stats(chat_id)
    if not stats:
        await update.message.reply_text("No mentions tracked yet.")
        return
    lines = ["Mention leaderboard:"]
    for i, (name, cnt) in enumerate(stats, start=1):
        lines.append(f"{i}. {name}: {cnt}")
    await update.message.reply_text("\n".join(lines))


def extract_mentions_from_entities(text: str, entities: List[MessageEntity]) -> List[Tuple[Optional[int], Optional[str], str]]:
    results: List[Tuple[Optional[int], Optional[str], str]] = []
    for ent in entities:
        if ent.type == MessageEntity.MENTION:  # @username in text
            username = text[ent.offset : ent.offset + ent.length].lstrip('@')
            if username:
                # Display as @username
                results.append((None, username, f"@{username}"))
        elif ent.type == MessageEntity.TEXT_MENTION and ent.user:  # text mention with actual user
            user = ent.user
            display = display_name_from_user(user)
            # username may be None
            results.append((user.id, user.username or None, display))
    return results


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg:
        return

    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        # Only track in group chats
        return

    entities = msg.entities or msg.caption_entities or []
    if not entities:
        return

    text = msg.text or msg.caption or ""
    mentions = extract_mentions_from_entities(text, entities)
    if not mentions:
        return

    for user_id, username, display in mentions:
        try:
            await increment_mention(chat.id, user_id, username, display)
        except Exception:
            logger.exception("Failed to increment mention for chat %s target %s/%s", chat.id, user_id, username)


async def main() -> None:
    token = os.getenv(TOKEN_ENV)
    if not token:
        raise RuntimeError(f"Please set {TOKEN_ENV} environment variable with your bot token.")

    application: Application = (
        ApplicationBuilder()
        .token(token)
        .post_init(_post_init)
        .build()
    )

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("stats", cmd_stats))

    # Listen to all text messages with entities (mentions)
    application.add_handler(MessageHandler(filters.TEXT & filters.Entity(MessageEntity.MENTION), handle_message))
    application.add_handler(MessageHandler(filters.TEXT & filters.Entity(MessageEntity.TEXT_MENTION), handle_message))

    # Also capture captions with entities (photos, etc.)
    application.add_handler(MessageHandler(filters.CaptionEntity(MessageEntity.MENTION), handle_message))
    application.add_handler(MessageHandler(filters.CaptionEntity(MessageEntity.TEXT_MENTION), handle_message))

    logger.info("Bot starting...")
    await application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
