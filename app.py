import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime

API_BASE_URL = "http://localhost:8000"  # Change to deployed URL if hosted


def fetch_arbitrage_data():
    try:
        response = requests.get(f"{API_BASE_URL}/arbitrage")
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and data.get("message") == "No opportunities found":
            return pd.DataFrame()
        if isinstance(data, list) and data:
            return pd.DataFrame(data)
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"API error: {e}")
        return pd.DataFrame()


# Page layout
st.title("Crypto Arbitrage Dashboard")

st.markdown("""
This dashboard displays real-time arbitrage opportunities across major exchanges for top crypto tokens (USDT pairs).
Data refreshes every 120 seconds. Minimum spread threshold: 0.5%.
""")

# Sidebar with FAQ and links
with st.sidebar:
    st.header("About This Tool")
    st.markdown("""
    **FAQ:**
    - **This dashboard monitors real-time arbitrage opportunities for top crypto tokens across major exchanges using USDT pairs.
    - **Data refreshes every 120 seconds from the backend API.
    - **Opportunities shown have a minimum price spread of 0.5%.
    - **For informational purposes only. Always DYOR and consider risks like fees and slippage.
    """)

    st.header("Links")
    st.link_button("Telegram Bot", "https://t.me/arb_spotter_bot")
    st.link_button("My X (Twitter)", "https://x.com/danny_4reel")

# Progress indicator while waiting for data
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False

placeholder = st.empty()
placeholder.info("Fetching latest data from API... Please wait.")

# Poll until data is available (with timeout)
max_attempts = 10  # ~20 seconds max wait
attempt = 0
df_arbitrage = pd.DataFrame()
while attempt < max_attempts and df_arbitrage.empty:
    df_arbitrage = fetch_arbitrage_data()
    if not df_arbitrage.empty:
        st.session_state.data_loaded = True
        break
    time.sleep(2)
    attempt += 1

placeholder.empty()  # Clear placeholder

if df_arbitrage.empty:
    st.warning(
        "No arbitrage opportunities found above the threshold. Retrying in 120 seconds...")
else:
    st.success("Data loaded successfully!")

    # Update timestamp
    st.session_state.last_update = time.time()
    st.info(
        f"Last Updated: {datetime.fromtimestamp(st.session_state.last_update).strftime('%Y-%m-%d %H:%M:%S')}")

    # Key Metrics (simple design enhancement)
    st.header("Overview")
    cols = st.columns(3)
    cols[0].metric("Total Opportunities", len(df_arbitrage))
    cols[1].metric(
        "Max Spread", f"{df_arbitrage['price_diff_pct'].max():.2f}%")
    cols[2].metric(
        "Avg Spread", f"{df_arbitrage['price_diff_pct'].mean():.2f}%")

    # Top 5 Opportunities Section
    st.header("Top 5 Arbitrage Opportunities")
    top_5 = df_arbitrage.head(5)
    for idx, row in top_5.iterrows():
        with st.expander(f"{idx+1}. {row['token']} - Spread: {row['price_diff_pct']:.2f}%"):
            st.write(f"**Buy Exchange:** {row['buy_exchange']}")
            st.write(f"**Buy Price:** ${row['buy_price']:.6f} USDT")
            st.write(f"**Sell Exchange:** {row['sell_exchange']}")
            st.write(f"**Sell Price:** ${row['sell_price']:.6f} USDT")
            st.write(
                f"**Profit per $1000:** ${row['profit_per_1000_usd']:.2f} USDT")

    # Best Opportunity Section
    best_row = df_arbitrage.iloc[0]
    st.header("Best Opportunity")
    st.subheader(f"Token: {best_row['token']}")
    st.write(
        f"**Buy on:** {best_row['buy_exchange']} at ${best_row['buy_price']:.6f} USDT")
    st.write(
        f"**Sell on:** {best_row['sell_exchange']} at ${best_row['sell_price']:.6f} USDT")
    st.write(f"**Spread:** {best_row['price_diff_pct']:.2f}%")

    # Profit Analysis Section
    st.header("Profit Analysis")
    st.markdown(
        "Calculate potential profits for different investment amounts. Adjust fees as needed.")

    # Small card for context
    with st.container(border=True):
        st.markdown(f"""
        **Best Opportunity:** {best_row['token']}  
        Buy {best_row['token']} on {best_row['buy_exchange']} at ${best_row['buy_price']:.2f}, Sell {best_row['token']} on {best_row['sell_exchange']} at ${best_row['sell_price']:.2f}  
        **Spread:** {best_row['price_diff_pct']:.3f}%
        """)

    fee_rate = st.slider(
        "Total Fees % (trading + withdrawal)", 0.0, 1.0, 0.2) / 100
    investments = [1000, 10000, 100000]  # Scalable investments
    data = []
    buy_price = best_row['buy_price']
    sell_price = best_row['sell_price']

    for investment in investments:
        units = investment / buy_price
        value = units * sell_price
        gross = value - investment
        fees = - (fee_rate * investment * 2)  # Assume fees on both sides
        net = gross + fees
        roi = (net / investment) * 100 if investment > 0 else 0
        data.append({
            "Investment": f"${investment:,.0f}",
            "Units": f"{units:.4f}",
            "Value": f"${value:,.2f}",
            "Gross": f"${gross:,.2f}",
            "Fees": f"${fees:,.2f}",
            "Net": f"${net:,.2f}",
            "ROI": f"{roi:.2f}%"
        })

    profit_df = pd.DataFrame(data)
    st.dataframe(profit_df, use_container_width=True)

# Footer
st.markdown("---")
st.caption(
    "Data sourced from CoinGecko API. For informational purposes only - not financial advice.")

# Auto-refresh after initial load
if st.session_state.data_loaded:
    time.sleep(120)
    st.rerun()
