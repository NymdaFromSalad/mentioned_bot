import asyncio
import logging

from telegram import Update
from telegram.ext import Application, ApplicationBuilder

from mentionbot.config import get_settings
from mentionbot.db import init_db as db_init, set_db_path
from mentionbot.handlers import register_handlers, default_commands


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def _post_init(app: Application) -> None:
    await db_init()
    # Set bot commands for menu
    try:
        await app.bot.set_my_commands(default_commands())
    except Exception:
        logger.exception("Failed to set bot commands")


def main() -> None:
    settings = get_settings()
    set_db_path(settings.db_path)

    application: Application = (
        ApplicationBuilder()
        .token(settings.token)
        .post_init(_post_init)
        .build()
    )

    register_handlers(application)

    logger.info("Bot starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        pass
