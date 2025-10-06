import pandas as pd
from utils import logging


def display_agg(df):
    """Aggregate trade data per exchange and print stats."""
    df_agg = df.groupby("exchange").agg(
        last_price_mean=("last_price", "mean"),
        last_vol_mean=("last_vol", "mean"),
        spread_mean=("spread", "mean"),
        num_trades=("last_price", "count")
    ).reset_index()
    df_agg = df_agg.round(2)
    logging.info("\n--- Aggregated Exchange Stats ---\n" + df_agg.to_string())
    return df_agg


def detect_arbitrage(df, min_profit_pct=0.5):
    """Detect arbitrage opportunities across exchanges for each token."""
    arbitrage_opps = []

    for token in df["token"].unique():
        df_token = df[df["token"] == token]
        if len(df_token) < 2:
            continue

        max_row = df_token.loc[df_token["last_price"].idxmax()]
        min_row = df_token.loc[df_token["last_price"].idxmin()]

        price_diff_pct = (
            (max_row["last_price"] - min_row["last_price"]) / min_row["last_price"]) * 100
        profit_per_unit = max_row["last_price"] - min_row["last_price"]
        # Calculate profit for $1000 investment
        quantity = 1000 / min_row["last_price"]  # Tokens bought with $1000
        profit_per_1000 = quantity * profit_per_unit

        if price_diff_pct >= min_profit_pct:
            arbitrage_opps.append({
                "token": token,
                "buy_exchange": min_row["exchange"],
                "buy_price": min_row["last_price"],
                "sell_exchange": max_row["exchange"],
                "sell_price": max_row["last_price"],
                "price_diff_pct": round(price_diff_pct, 2),
                "profit_per_1000_usd": round(profit_per_1000, 2)
            })

    if arbitrage_opps:
        df_arbitrage = pd.DataFrame(arbitrage_opps)
        logging.info("\n--- Arbitrage Opportunities ---\n" +
                     df_arbitrage.to_string())
        return df_arbitrage
    else:
        logging.info("\nNo arbitrage opportunities found above threshold.")
        return pd.DataFrame()