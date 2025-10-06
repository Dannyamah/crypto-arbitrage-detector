import os
from dotenv import load_dotenv
from bot import run_bot_dynamic, start_telegram_bot
import threading
from utils import logging

load_dotenv()

# Run the dynamic loop in a thread
try:
    dynamic_thread = threading.Thread(target=run_bot_dynamic, args=(300,))
    dynamic_thread.daemon = True
    dynamic_thread.start()
except Exception as e:
    logging.error(f"Failed to start dynamic loop: {e}")

# Run Telegram bot polling in the main thread
start_telegram_bot()
