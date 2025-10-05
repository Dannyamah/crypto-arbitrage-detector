from fastapi import FastAPI
import pandas as pd
import threading
import time
import os
from dotenv import load_dotenv
from api import get_top_tokens, get_exchanges, get_all_tickers
from aggregation import detect_arbitrage, display_agg
from utils import convert_to_local_tz, logging

load_dotenv()

app = FastAPI(title="Arbitrage API")
latest_df_all = pd.DataFrame()
latest_df_arbitrage = pd.DataFrame()
latest_timestamp = None


def background_scan(interval_sec=120, min_profit_pct=0.5, refresh_interval_loops=60):
    global latest_df_all, latest_df_arbitrage, latest_timestamp
    logging.info("Starting background arbitrage scan...")
    top_tokens = get_top_tokens(100)
    top_exchanges = get_exchanges(top_n=10)
    loop_count = 0
    while True:
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
        latest_df_all = df_all
        latest_timestamp = time.time()

        if not df_all.empty:
            display_agg(df_all)
            df_arbitrage = detect_arbitrage(
                df_all, min_profit_pct=min_profit_pct)
            latest_df_arbitrage = df_arbitrage.sort_values(
                by="price_diff_pct", ascending=False)

        logging.info(f"Scan complete. Waiting {interval_sec} seconds...")
        time.sleep(interval_sec)
        loop_count += 1


# Start background scan in a thread
threading.Thread(target=background_scan, daemon=True).start()


@app.get("/arbitrage")
def get_arbitrage():
    if latest_df_arbitrage.empty:
        return {"message": "No opportunities found"}
    return latest_df_arbitrage.to_dict(orient="records")


@app.get("/status")
def get_status():
    return {
        "running": True,
        "last_scan_time": latest_timestamp,
        "opportunities_count": len(latest_df_arbitrage)
    }
