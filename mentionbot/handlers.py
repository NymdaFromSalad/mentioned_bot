import logging
from typing import List, Optional, Tuple

from telegram import Update, MessageEntity, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from .db import increment_mention, get_stats

logger = logging.getLogger(__name__)


def display_name_from_user(user) -> str:
    if user is None:
        return "Неизвестно"
    if getattr(user, "username", None):
        return f"@{user.username}"
    name = (user.first_name or "").strip()
    if getattr(user, "last_name", None):
        name = f"{name} {user.last_name}".strip()
    return name or str(user.id)


def extract_mentions_from_entities(text: str, entities: List[MessageEntity]) -> List[Tuple[Optional[int], Optional[str], str]]:
    results: List[Tuple[Optional[int], Optional[str], str]] = []
    for ent in entities:
        if ent.type == MessageEntity.MENTION:
            username = text[ent.offset : ent.offset + ent.length].lstrip("@")
            if username:
                results.append((None, username, f"@{username}"))
        elif ent.type == MessageEntity.TEXT_MENTION and ent.user:
            user = ent.user
            display = display_name_from_user(user)
            results.append((user.id, user.username or None, display))
    return results


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    text = (
        "Этот бот считает, сколько раз участников упоминали в каждом чате.\n"
        "- Добавьте бота в чат\n"
        "- Упоминайте с помощью @username или текстового упоминания.\n"
        "- Используйте команду /stats, чтобы посмотреть таблицу лидеров.\n"
        "Статистика ведётся отдельно для каждого чата и хранится в SQLite."
    )
    await update.message.reply_text(text)


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not update.message:
        return
    chat_id = update.effective_chat.id
    stats = await get_stats(chat_id)
    if not stats:
        await update.message.reply_text("Пока нет упоминаний.")
        return
    lines = ["Топ упоминаний:"]
    for i, (name, cnt) in enumerate(stats, start=1):
        lines.append(f"{i}. {name}: {cnt}")
    await update.message.reply_text("\n".join(lines))


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    text = (
        "Этот бот считает, сколько раз участников упоминали в каждом чате.\n"
        "- Добавьте бота в чат\n"
        "- Упоминайте с помощью @username или текстового упоминания.\n"
        "- Используйте команду /stats, чтобы посмотреть таблицу лидеров.\n"
        "Статистика ведётся отдельно для каждого чата и хранится в SQLite."
    )
    await update.message.reply_text(text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg:
        return

    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
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
            logger.exception(
                "Failed to increment mention for chat %s target %s/%s",
                chat.id,
                user_id,
                username,
            )


def register_handlers(application: Application) -> None:
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("stats", cmd_stats))
    application.add_handler(CommandHandler("help", cmd_help))

    application.add_handler(MessageHandler(filters.TEXT & filters.Entity(MessageEntity.MENTION), handle_message))
    application.add_handler(MessageHandler(filters.TEXT & filters.Entity(MessageEntity.TEXT_MENTION), handle_message))

    application.add_handler(MessageHandler(filters.CaptionEntity(MessageEntity.MENTION), handle_message))
    application.add_handler(MessageHandler(filters.CaptionEntity(MessageEntity.TEXT_MENTION), handle_message))


def default_commands() -> list[BotCommand]:
    return [
        BotCommand("start", "Помощь"),
        #BotCommand("help", "Помощь"),
        BotCommand("stats", "Статистика упоминаний"),
    ]
