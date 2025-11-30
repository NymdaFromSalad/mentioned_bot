# MentionBot

A Telegram bot that counts how many times users are mentioned in a group/supergroup chat and shows a per-chat leaderboard. Mentions are stored in SQLite.

## Features

- Tracks both `@username` mentions and text mentions (MessageEntity.TEXT_MENTION)
- Per-chat statistics in SQLite (`mentions.sqlite3` by default)
- `/stats` command to display the leaderboard

## Requirements

- Python 3.10+
- A Telegram Bot Token from @BotFather

## Setup

1. Create and activate a virtual environment (optional but recommended)

```bash
python -m venv .venv
. .venv/Scripts/activate  # on Windows PowerShell: .venv\Scripts\Activate.ps1
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Configure environment

- Option A: use a `.env` file (recommended)
  - Copy `.env.example` to `.env` and fill in values
  - `TELEGRAM_BOT_TOKEN=123456:ABC-Your-Bot-Token`
  - `MENTION_BOT_DB=mentions.sqlite3` (optional)

- Option B: set environment variables directly (Windows PowerShell):
  ```powershell
  $env:TELEGRAM_BOT_TOKEN = "123456:ABC-Your-Bot-Token"
  $env:MENTION_BOT_DB = "d:\\Python\\mentionbot\\mentions.sqlite3"  # optional
  ```

## Run

```bash
python main.py
```

Invite the bot to your group or supergroup, grant it permission to read messages. Mention users using `@username` or use text mentions. Use `/stats` to see the leaderboard for that chat.

## Notes

- Only counts mentions in group/supergroup chats.
- Usernames are normalized to lowercase for uniqueness; display name is preserved.
- The leaderboard is limited to top 50 for readability.

## Project structure

```
mentionbot/
  __init__.py
  config.py        # loads settings from .env/env
  db.py            # sqlite storage and queries
  handlers.py      # bot command and message handlers
main.py            # entrypoint
requirements.txt
.env.example
README.md
```
