import os
from dataclasses import dataclass
from typing import Optional

try:
    # Optional, only if python-dotenv is installed
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
    load_dotenv = None  # type: ignore


def load_env() -> None:
    # Load from .env if available
    if load_dotenv is not None:
        load_dotenv()


@dataclass
class Settings:
    token: str
    db_path: str


def get_settings() -> Settings:
    load_env()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set. Put it in environment or .env file.")
    db_path = os.getenv("MENTION_BOT_DB", "mentions.sqlite3")
    return Settings(token=token, db_path=db_path)
