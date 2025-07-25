# Crypto Analyst Terminal Bot

A web-based terminal-style AI bot that provides comprehensive crypto asset analysis similar to a senior analyst from Goldman Sachs, ARK Invest, Delphi Digital, or Messari.

## Features

* Overview summary (price, market cap, volume, supply, utility)
* Technical analysis (SMA, EMA, RSI, MACD, Bollinger Bands, support/resistance, ASCII chart)
* Sentiment (Fear & Greed Index)
* Skeletons for social sentiment, whale activity, on-chain metrics, tokenomics (placeholders for future integration)

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the server
python main.py

# 3. Open your browser
Visit http://localhost:8000 and start typing commands, e.g.:
> Analyze BTC
> Breakdown ETH
```

## Notes & Limitations

* Data is fetched from CoinGecko (no API key required).
* Some advanced metrics (social sentiment, whale activity, tokenomics, on-chain) require paid APIs and are marked as not implemented.
* Technical indicators are computed with `pandas_ta`. ASCII price chart is created with `sparklines`.
* This is a prototype showcasing the structure; production usage should add caching, error handling, and rate-limit management.