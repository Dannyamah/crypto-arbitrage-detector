import os
from dotenv import load_dotenv
from api import get_top_tokens, get_exchanges
from bot import run_bot_dynamic, start_telegram_bot
import threading
from utils import logging

load_dotenv()

# Fetch initial dynamic token list
TOP_TOKENS = get_top_tokens(100)  # Increased to top 100 tokens

# Top exchanges by BTC volume
TOP_EXCHANGES = get_exchanges(top_n=10)  # Increased to top 10 exchanges

# Start Telegram bot in a separate thread
try:
    telegram_thread = threading.Thread(
        target=start_telegram_bot, args=(TOP_TOKENS, TOP_EXCHANGES))
    telegram_thread.daemon = True  # Exit when main thread exits
    telegram_thread.start()
except Exception as e:
    logging.error(f"Failed to start Telegram bot: {e}")

# Run main bot loop
run_bot_dynamic(
    TOP_TOKENS,
    TOP_EXCHANGES,
    interval_sec=120,
    min_profit_pct=0.5,
    refresh_interval_loops=60
)
