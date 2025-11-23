# TGbotTr8Energy

Telegram bot for renting and providing TRON energy using aiogram 3, aiohttp, and SQLite.

## Features
- Main menu with Buy Energy, Provide Energy, FAQ, and Our Tools shortcuts.
- Buy energy flow with TRON address validation, wallet info preview, mocked energy packages, and invoice generation with commission.
- Background invoice watcher that simulates payment confirmation and delegates energy (placeholder).
- Provide energy helper that reviews wallet resources and guides users to tr8.energy or educational material.
- Friendly FAQ and promotion of partner tools.

## Quick start
1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill in your values:
   ```bash
   cp .env.example .env
   ```

3. Run the bot:
   ```bash
   python bot.py
   ```

## Environment variables
- `BOT_TOKEN` (required): Telegram bot token.
- `COMMISSION_PERCENT` (default `10`): Percentage added to base package price.
- `DATABASE_PATH` (default `bot_data.sqlite3`): SQLite file path.
- `PAYMENT_CHECK_INTERVAL_SEC` (default `30`): Seconds between payment checks.
- `SIMULATE_PAYMENTS` (default `true`): If true, invoices auto-complete after ~1 minute (placeholder until real Tron watcher is added).

## Notes
- TRON RPC and tronsave.io integrations are mocked. Replace TODO sections in `app/tron_client.py`, `app/tronsave_client.py`, and `app/payment.py` with real implementations.
- Payment addresses are placeholders; wire up real generation before production use.
