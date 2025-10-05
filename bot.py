import time
import pandas as pd
import json
from datetime import datetime
from utils import convert_to_local_tz, logging
import requests
import asyncio
from telegram.ext import Application, CommandHandler
from telegram import Update
from dotenv import load_dotenv
import os

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = 706456243  # Your admin chat ID
API_BASE_URL = "http://localhost:8000"  # Change to deployed URL

# Global flag to control bot loop
running = True

# In-memory set for subscribed user chat IDs
subscribed_chats = set()

# Cache for latest scan data (optional, since API is primary)
latest_scan_data = {"df_all": None, "timestamp": None}

SUBSCRIPTIONS_FILE = "subscriptions.json"


def load_subscriptions():
    """Load subscribed chats from JSON file."""
    global subscribed_chats
    if os.path.exists(SUBSCRIPTIONS_FILE):
        with open(SUBSCRIPTIONS_FILE, 'r') as f:
            subscribed_chats = set(json.load(f))
        logging.info(f"Loaded {len(subscribed_chats)} subscriptions.")
    else:
        logging.info("No subscriptions file found. Starting with empty set.")


def save_subscriptions():
    """Save subscribed chats to JSON file."""
    with open(SUBSCRIPTIONS_FILE, 'w') as f:
        json.dump(list(subscribed_chats), f)
    logging.info(f"Saved {len(subscribed_chats)} subscriptions.")


async def start(update: Update, context):
    """Send intro message on /start."""
    message = (
        "Welcome to the Crypto Arbitrage Bot! 📈\n"
        "This bot monitors top tokens across major exchanges for arbitrage opportunities.\n"
        "Use /subscribe to receive auto-loop alerts.\n"
        "Use /unsubscribe to stop receiving alerts.\n"
        "Use /scan_opportunities to check manually (uses latest cached data).\n"
        "Use /status to check bot status.\n"
        "Admins: Use /stop or /restart for the continuous scan."
    )
    await update.message.reply_text(message)


async def subscribe(update: Update, context):
    """Subscribe to auto-loop alerts."""
    chat_id = update.message.chat_id
    subscribed_chats.add(chat_id)
    save_subscriptions()
    await update.message.reply_text("Subscribed to arbitrage alerts!")


async def unsubscribe(update: Update, context):
    """Unsubscribe from auto-loop alerts."""
    chat_id = update.message.chat_id
    subscribed_chats.discard(chat_id)
    save_subscriptions()
    await update.message.reply_text("Unsubscribed from arbitrage alerts.")


async def stop(update: Update, context):
    """Stop the continuous arbitrage scan (admin only)."""
    if update.message.chat_id != ADMIN_CHAT_ID:
        await update.message.reply_text("Only admins can stop the bot.")
        return
    global running
    running = False
    await update.message.reply_text("Continuous arbitrage scan stopped. Use /restart to resume.")


async def restart(update: Update, context):
    """Restart the continuous arbitrage scan (admin only)."""
    if update.message.chat_id != ADMIN_CHAT_ID:
        await update.message.reply_text("Only admins can restart the bot.")
        return
    global running
    running = True
    await update.message.reply_text("Continuous arbitrage scan restarted.")


async def status(update: Update, context):
    """Report bot status."""
    try:
        response = requests.get(f"{API_BASE_URL}/status")
        response.raise_for_status()
        api_status = response.json()
        last_scan_time = datetime.fromtimestamp(api_status["last_scan_time"]).strftime(
            "%Y-%m-%d %H:%M:%S") if api_status["last_scan_time"] else "No scan yet"
    except Exception:
        last_scan_time = "API unavailable"

    message = (
        f"Bot Status:\n"
        f"Running: {'Yes' if running else 'No'}\n"
        f"Last Scan: {last_scan_time}\n"
        f"Subscribers: {len(subscribed_chats)}\n"
    )
    await update.message.reply_text(message)


async def scan_opportunities(update: Update, context):
    """Run arbitrage scan using API data and send results."""
    try:
        response = requests.get(f"{API_BASE_URL}/arbitrage")
        response.raise_for_status()
        data = response.json()
        df_arbitrage = pd.DataFrame(data) if data and isinstance(
            data, list) else pd.DataFrame()

        if df_arbitrage.empty:
            await update.message.reply_text("No arbitrage opportunities found above threshold. 📉")
        else:
            message = "⚡ Arbitrage Opportunities Found! 📈\n\n"
            for _, row in df_arbitrage.iterrows():
                message += (
                    f"💸 Token: {row['token']}\n"
                    f"💰 Buy: {row['buy_exchange']} @ {row['buy_price']:.6f} USDT\n"
                    f"💰 Sell: {row['sell_exchange']} @ {row['sell_price']:.6f} USDT\n"
                    f"📈 Price Diff: {row['price_diff_pct']:.2f}%\n"
                    f"💵 Profit/$1000: {row['profit_per_1000_usd']:.2f} USDT\n\n"
                )
            logging.info(f"Sending Telegram message:\n{message}")
            await update.message.reply_text(message)
    except Exception as e:
        await update.message.reply_text(f"Error fetching data from API: {e}")


async def log_chat_id(update: Update, context):
    """Log chat ID for debugging."""
    chat_id = update.message.chat_id
    logging.info(f"Chat ID: {chat_id}")
    await update.message.reply_text(f"Your chat ID is: {chat_id}")


def send_telegram_message(message):
    """Send message to all subscribed chats."""
    if not TELEGRAM_BOT_TOKEN:
        logging.warning("Telegram creds missing; skipping alert.")
        return
    for chat_id in subscribed_chats:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message
        }
        try:
            resp = requests.post(url, json=payload)
            resp.raise_for_status()
            logging.info(f"Telegram message sent to {chat_id} successfully.")
        except Exception as e:
            logging.error(f"Telegram send to {chat_id} failed: {e}")


def send_error_alert(error_msg):
    """Send error alert to admin."""
    if not TELEGRAM_BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    message = f"Bot Error Alert: {error_msg}"
    payload = {
        "chat_id": ADMIN_CHAT_ID,
        "text": message
    }
    try:
        resp = requests.post(url, json=payload)
        resp.raise_for_status()
        logging.info("Error alert sent to admin.")
    except Exception as e:
        logging.error(f"Failed to send error alert: {e}")


def run_bot_dynamic(interval_sec=120):
    """Updated loop to query FastAPI instead of fetching data."""
    global running
    while running:
        try:
            response = requests.get(f"{API_BASE_URL}/arbitrage")
            response.raise_for_status()
            data = response.json()
            df_arbitrage = pd.DataFrame(data) if data and isinstance(
                data, list) else pd.DataFrame()

            if not df_arbitrage.empty:
                message = "⚡ Arbitrage Opportunities Found! 📈\n\n"
                for _, row in df_arbitrage.iterrows():
                    message += (
                        f"💸 Token: {row['token']}\n"
                        f"💰 Buy: {row['buy_exchange']} @ {row['buy_price']:.6f} USDT\n"
                        f"💰 Sell: {row['sell_exchange']} @ {row['sell_price']:.6f} USDT\n"
                        f"📈 Price Diff: {row['price_diff_pct']:.2f}%\n"
                        f"💵 Profit/$1000: {row['profit_per_1000_usd']:.2f} USDT\n\n"
                    )
                logging.info(f"Sending Telegram message:\n{message}")
                send_telegram_message(message)
        except Exception as e:
            logging.error(f"Failed to fetch from API: {e}")
            send_error_alert(str(e))

        logging.info(f"Waiting {interval_sec} seconds before next update...")
        time.sleep(interval_sec)

    logging.info("Arbitrage alert loop stopped via /stop command.")


def start_telegram_bot():
    """Start Telegram bot to handle commands."""
    if not TELEGRAM_BOT_TOKEN:
        logging.error(
            "TELEGRAM_BOT_TOKEN not set. Telegram bot will not start.")
        return
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))
    app.add_handler(CommandHandler("scan_opportunities", scan_opportunities))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("restart", restart))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("getid", log_chat_id))  # Debug chat ID
    app.run_polling()


# Load subscriptions on startup
load_subscriptions()
