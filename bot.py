import time
import pandas as pd
import json
import os
from datetime import datetime
from api import get_all_tickers, get_top_tokens, get_exchanges
from aggregation import display_agg, detect_arbitrage
from utils import convert_to_local_tz, logging
import requests
import asyncio
from telegram.ext import Application, CommandHandler
from telegram import Update

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = 706456243  # Your admin chat ID

# Global flag to control bot loop
running = True

# In-memory set for subscribed user chat IDs
subscribed_chats = set()

# Cache for latest scan data
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
    last_scan_time = datetime.fromtimestamp(latest_scan_data["timestamp"]).strftime(
        "%Y-%m-%d %H:%M:%S") if latest_scan_data["timestamp"] else "No scan yet"
    message = (
        f"Bot Status:\n"
        f"Running: {'Yes' if running else 'No'}\n"
        f"Last Scan: {last_scan_time}\n"
        f"Subscribers: {len(subscribed_chats)}\n"
    )
    await update.message.reply_text(message)


async def scan_opportunities(update: Update, context):
    """Run arbitrage scan using cached data and send results."""
    if latest_scan_data["df_all"] is None or latest_scan_data["timestamp"] is None:
        await update.message.reply_text("No recent data available. Please wait for the next scan cycle.")
        return

    # Check if data is recent (within 120 seconds to match new interval)
    current_time = time.time()
    if current_time - latest_scan_data["timestamp"] > 120:
        await update.message.reply_text("Data is outdated. Please wait for the next scan cycle.")
        return

    df_all = latest_scan_data["df_all"]
    if df_all.empty:
        await update.message.reply_text("No tickers found in the latest scan.")
        return

    df_arbitrage = detect_arbitrage(
        df_all, min_profit_pct=0.5)  # Updated to 0.5%
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


def run_bot_dynamic(top_tokens, top_exchanges, interval_sec=120, min_profit_pct=0.5, refresh_interval_loops=60):
    """
    Tracks top traded tokens across multiple exchanges and detects arbitrage.
    Prices are taken only from USDT pairs for consistency.
    """
    global running, latest_scan_data
    logging.info(
        f"Tracking {len(top_tokens)} tokens on {len(top_exchanges)} exchanges...")

    loop_count = 0
    while running:
        if loop_count % refresh_interval_loops == 0:
            logging.info("Refreshing top tokens and exchanges...")
            top_tokens = get_top_tokens(len(top_tokens))
            top_exchanges = get_exchanges(len(top_exchanges))

        all_data = []
        for ex in top_exchanges:
            tickers = get_all_tickers(ex["id"])
            for ticker in tickers:
                base = ticker.get("base", "").upper()
                target = ticker.get("target", "").upper()
                if base not in top_tokens or target != "USDT":
                    continue
                last_price = float(ticker.get("last", 0) or 0)
                if last_price == 0:
                    continue
                all_data.append({
                    "exchange": ex["id"],
                    "token": base,
                    "last_price": last_price,
                    "last_vol": float(ticker.get("volume", 0) or 0),
                    "spread": float(ticker.get("bid_ask_spread_percentage", 0) or 0),
                    "trade_time": convert_to_local_tz(ticker.get("last_traded_at"))
                })

        df_all = pd.DataFrame(all_data)
        # Cache the latest scan data
        latest_scan_data["df_all"] = df_all
        latest_scan_data["timestamp"] = time.time()

        if df_all.empty:
            logging.info("No tickers found this round.")
        else:
            display_agg(df_all)
            df_arbitrage = detect_arbitrage(
                df_all, min_profit_pct=min_profit_pct)
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

        logging.info(f"Waiting {interval_sec} seconds before next update...")
        time.sleep(interval_sec)
        loop_count += 1

    logging.info("Arbitrage scan stopped via /stop command.")


def start_telegram_bot(top_tokens, top_exchanges):
    """Start Telegram bot to handle commands."""
    if not TELEGRAM_BOT_TOKEN:
        logging.error(
            "TELEGRAM_BOT_TOKEN not set. Telegram bot will not start.")
        return
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.bot_data["top_tokens"] = top_tokens
    app.bot_data["top_exchanges"] = top_exchanges
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
