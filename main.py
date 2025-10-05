import os
from dotenv import load_dotenv
from bot import run_bot_dynamic, start_telegram_bot
import threading
from utils import logging

load_dotenv()

# Start Telegram bot in a separate thread
try:
    telegram_thread = threading.Thread(target=start_telegram_bot)
    telegram_thread.daemon = True
    telegram_thread.start()
except Exception as e:
    logging.error(f"Failed to start Telegram bot: {e}")

# Run main bot loop (now queries API)
run_bot_dynamic(interval_sec=120)
