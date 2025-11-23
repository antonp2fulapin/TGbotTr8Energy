# TGbotTr8Energy

Telegram bot for renting and providing TRON energy using aiogram 3, aiohttp, and SQLite.

## Features
- Main menu with Buy Energy, Provide Energy, FAQ, and Our Tools shortcuts.
- Buy energy flow with TRON address validation, live wallet info preview, tronsave.io package fetch, and invoice generation with commission.
- Background invoice watcher that polls TronGrid for payments and triggers tronsave.io delegation.
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
- `SIMULATE_PAYMENTS` (default `true`): If true, invoices auto-complete after ~1 minute; set to `false` to rely on TronGrid polling.
- `PAYMENT_RECEIVER_ADDRESS` (required for real payments): TRON address where users should send TRX.
- `TRON_API_BASE` (default `https://api.trongrid.io`): TronGrid base URL.
- `TRON_API_KEY` (optional): TronGrid API key header `TRON-PRO-API-KEY`.
- `TRONSAVE_API_BASE` (default `https://tronsave.io`): tronsave.io API base.
- `TRONSAVE_API_KEY` (optional): tronsave.io bearer token.

## Notes
- TRON RPC and tronsave.io integrations now use live HTTP calls; ensure the API endpoints and keys are configured before production.
- Payment detection polls TronGrid for transfers to `PAYMENT_RECEIVER_ADDRESS` and matches invoice amounts.
