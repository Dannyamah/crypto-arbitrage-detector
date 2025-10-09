# Crypto Arbitrage Detector (ArbSpotter)
A real-time tool to detect arbitrage opportunities across crypto exchanges using CoinGecko API.
It scans prices for top tokens (USDT pairs), computes spreads (>0.5%), sends Telegram alerts, and visualizes data in a React dashboard.

## Features
- Backend: Fetches and aggregates data, detects opps in background loop.
- Telegram Bot: Commands for subscription, manual scans, alerts.
- Frontend: React dashboard with tables, metrics, profit calculator, search/sort, dark mode.
- Deployment-ready on Railway (API, bot, frontend as separate services).

## Prerequisites
- Python 3.10+ (with pip).
- Node.js 18+ (with npm).
- CoinGecko API key: Get one [here](https://docs.coingecko.com/docs/setting-up-your-api-key) (free/demo or pro plans available).
- Telegram Bot Token: Create a bot via [BotFather](https://t.me/botfather) on Telegram—send /newbot, follow prompts to get the token.
- Git.

## Installation
1. Clone the repo:
   ```
   git clone https://github.com/Dannyamah/crypto-arbitrage-detector.git
   cd crypto-arbitrage-detector
   ```

2. **Backend Setup** (in root or backend folder):
   - Install deps: `pip install -r requirements.txt`
   - Create `.env`:
     ```
     COINGECKO_API=your_coingecko_key
     TELEGRAM_BOT_TOKEN=your_bot_token
     API_URL=http://localhost:8000 # For local bot-API comms
     ```
   - **API Configuration Note**: If using a free/demo CoinGecko key, edit `api.py`:
     - Change `coingecko_url` to
      `coingecko_url = "https://api.coingecko.com/api/v3"`
     - Update headers to:
       ```
       headers = {
           "accept": "application/json",
           "x-cg-demo-api-key": COINGECKO_API
       }
       ```

3. **Frontend Setup** (in frontend folder):
   - Install deps: `npm install`
   - Create `.env`:
     ```
     REACT_APP_API_URL=http://localhost:8000
     ```

## Running Locally
1. **Start Backend API** (in backend root): `fastapi dev server.py` (runs on http://localhost:8000). Test: Visit /arbitrage.
2. **Start Telegram Bot** (in backend root, API must run): `python main.py`. Interact via Telegram (/start, /subscribe, etc.).
3. **Start Frontend** (in frontend root): `npm start` (runs on http://localhost:3000). Dashboard fetches from local API.

## Configuration Notes
- Intervals: Backend/bot scan every 300s (5 min)—adjust in server.py/bot.py/main.py.
- Cache: Uses cache.json (ephemeral locally).
- Errors: Check bot.log for issues (e.g., API keys, rate limits).

## Contributing
Contributions are welcome!
To contribute:
1. Fork the repository
2. Create your feature branch (`git checkout -b feature-name`)
3. Commit your changes
4. Open a Pull Request

## License
This project is licensed under the terms of the MIT License.

## Connect
- [X (Twitter)](https://x.com/danny_4reel)
- [Linkedin](https://www.linkedin.com/in/dannyamah)
- [Personal Website](https://daniel-amah.vercel.app)

---
