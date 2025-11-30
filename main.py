import asyncio
import logging

from telegram import Update
from telegram.ext import Application, ApplicationBuilder

from mentionbot.config import get_settings
from mentionbot.db import init_db as db_init, set_db_path
from mentionbot.handlers import register_handlers


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    set_db_path(settings.db_path)
    await db_init()

    application: Application = (
        ApplicationBuilder()
        .token(settings.token)
        .build()
    )

    register_handlers(application)

    logger.info("Bot starting...")
    await application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
