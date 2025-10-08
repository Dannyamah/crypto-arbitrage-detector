import requests
import os
import time
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from utils import logging

load_dotenv()
COINGECKO_API = os.getenv("COINGECKO_API")
coingecko_url = "https://pro-api.coingecko.com/api/v3"
headers = {
    "accept": "application/json",
    "x-cg-pro-api-key": COINGECKO_API
}

CACHE_FILE = "cache.json"
CACHE_TTL = timedelta(hours=6)  # Cache tokens/exchanges for 6 hours


def api_request(url, params=None, retries=5):
    """Helper for API calls with retries and backoff."""
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, headers=headers)
            if resp.status_code == 429:
                logging.error("Rate limit hit (429). Backing off.")
                # Exponential backoff: 2s, 4s, 8s, 16s, 32s
                time.sleep(2 ** (attempt + 1))
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"API request failed: {e}")
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)  # Exponential backoff
    time.sleep(1.0)  # Increased delay to avoid rate limits


def load_cache():
    """Load cached tokens/exchanges if not expired."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            cache = json.load(f)
        cache_time = datetime.fromtimestamp(cache['timestamp'])
        if datetime.now() - cache_time < CACHE_TTL:
            logging.info("Using cached tokens and exchanges.")
            return cache['top_tokens'], cache['top_exchanges']
    return None, None


def save_cache(top_tokens, top_exchanges):
    """Save tokens/exchanges to cache."""
    cache = {
        'top_tokens': top_tokens,
        'top_exchanges': top_exchanges,
        'timestamp': time.time()
    }
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f)
    logging.info("Cached tokens and exchanges.")


def get_exchanges(top_n=5):
    """Return top exchanges sorted by 24h BTC volume."""
    params = {"per_page": 250, "page": 1}
    data = api_request(f"{coingecko_url}/exchanges", params)
    exchanges = sorted(data, key=lambda x: x.get(
        "trade_volume_24h_btc", 0), reverse=True)
    return exchanges[:top_n]


def get_top_tokens(n=50):
    """Fetch top N tokens by 24h USD trading volume."""
    url = f"{coingecko_url}/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "volume_desc",
        "per_page": n,
        "page": 1
    }
    data = api_request(url, params)
    return [coin["symbol"].upper() for coin in data]


def get_all_tickers(exchange_id):
    """Return all tickers for a given exchange."""
    try:
        data = api_request(f"{coingecko_url}/exchanges/{exchange_id}/tickers")
        return data.get("tickers", [])
    except Exception as e:
        logging.error(f"Failed to fetch tickers for {exchange_id}: {e}")
        return []
