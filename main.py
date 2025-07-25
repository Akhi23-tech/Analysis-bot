import json
import time
from datetime import datetime
from functools import lru_cache

import numpy as np
import pandas as pd
import pandas_ta as ta
import requests
from flask import Flask, jsonify, request, send_from_directory
from sparklines import sparklines

app = Flask(__name__, static_folder="static", static_url_path="")

COINGECKO_API = "https://api.coingecko.com/api/v3"
FNG_API = "https://api.alternative.me/fng/?limit=1"

# ---------------------------------------------------
# Utility helpers
# ---------------------------------------------------

def human_format(num):
    """Format large numbers into human-readable strings."""
    num = float(num)
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return f"{num:.2f}{['', 'K', 'M', 'B', 'T'][magnitude]}"


@lru_cache(maxsize=1)
def get_coin_list():
    resp = requests.get(f"{COINGECKO_API}/coins/list")
    resp.raise_for_status()
    return resp.json()


def symbol_to_id(symbol):
    symbol = symbol.lower()
    for coin in get_coin_list():
        if coin["symbol"].lower() == symbol:
            return coin["id"]
    return None


def fetch_market_overview(coin_id):
    resp = requests.get(
        f"{COINGECKO_API}/coins/{coin_id}",
        params={
            "localization": "false",
            "tickers": "false",
            "market_data": "true",
            "community_data": "false",
            "developer_data": "false",
            "sparkline": "false",
        },
    )
    resp.raise_for_status()
    data = resp.json()
    md = data["market_data"]
    overview = {
        "name": data.get("name"),
        "symbol": data.get("symbol").upper(),
        "current_price": md["current_price"]["usd"],
        "market_cap": md["market_cap"]["usd"],
        "volume_24h": md["total_volume"]["usd"],
        "circulating_supply": md.get("circulating_supply"),
        "total_supply": md.get("total_supply"),
        "description": data.get("description", {}).get("en", "")[:400],
    }
    return overview


def fetch_ohlc(coin_id, days=365):
    resp = requests.get(
        f"{COINGECKO_API}/coins/{coin_id}/market_chart",
        params={"vs_currency": "usd", "days": days, "interval": "daily"},
    )
    resp.raise_for_status()
    prices = resp.json()["prices"]  # list of [timestamp, price]
    df = pd.DataFrame(prices, columns=["ts", "close"])
    df["date"] = pd.to_datetime(df["ts"], unit="ms")
    df.set_index("date", inplace=True)
    return df[["close"]]


def compute_technicals(df):
    df_ta = df.copy()
    df_ta["SMA20"] = ta.sma(df_ta["close"], length=20)
    df_ta["SMA50"] = ta.sma(df_ta["close"], length=50)
    df_ta["SMA200"] = ta.sma(df_ta["close"], length=200)
    df_ta["EMA20"] = ta.ema(df_ta["close"], length=20)
    df_ta["EMA50"] = ta.ema(df_ta["close"], length=50)
    df_ta["EMA200"] = ta.ema(df_ta["close"], length=200)
    df_ta["RSI"] = ta.rsi(df_ta["close"], length=14)
    macd = ta.macd(df_ta["close"])
    df_ta = pd.concat([df_ta, macd], axis=1)
    bb = ta.bbands(df_ta["close"])
    df_ta = pd.concat([df_ta, bb], axis=1)
    return df_ta


def build_ascii_chart(series, width=60):
    # Downsample series to the desired width
    if len(series) < width:
        return sparklines(series)[0]
    step = len(series) // width
    sampled = series[::step]
    return sparklines(sampled)[0]


def analyze_asset(symbol):
    coin_id = symbol_to_id(symbol)
    if not coin_id:
        return f"❌ Asset symbol '{symbol}' not found on CoinGecko."

    # Overview
    overview = fetch_market_overview(coin_id)

    # Historical + technicals
    df = fetch_ohlc(coin_id)
    df_ta = compute_technicals(df)
    latest = df_ta.iloc[-1]

    # Support / Resistance: simple high/low over 30 days
    recent_window = df["close"].tail(30)
    support = recent_window.min()
    resistance = recent_window.max()

    # Volume analysis placeholder (CoinGecko daily volume not provided in OHLC endpoint)

    # Sentiment: Fear & Greed Index
    try:
        fng = requests.get(FNG_API, timeout=10).json()["data"][0]
        fear_greed = fng["value"]
        fng_text = fng["value_classification"]
    except Exception:
        fear_greed = "N/A"
        fng_text = "Unavailable"

    # Assemble report
    lines = []
    lines.append("⸻")
    lines.append(f"🪙 Overview — {overview['name']} ({overview['symbol']})")
    lines.append(f"Price: ${overview['current_price']:,} | Market Cap: ${human_format(overview['market_cap'])} | 24h Vol: ${human_format(overview['volume_24h'])}")
    lines.append(
        f"Supply: {human_format(overview['circulating_supply'])} / {human_format(overview['total_supply']) if overview['total_supply'] else '∞'}"
    )
    if overview["description"]:
        lines.append(f"Utility: {overview['description'].replace(chr(10), ' ') }…")

    lines.append("\n📈 Technical Analysis")
    lines.append(
        f"SMA(20/50/200): {latest['SMA20']:.2f}, {latest['SMA50']:.2f}, {latest['SMA200']:.2f}")
    lines.append(
        f"EMA(20/50/200): {latest['EMA20']:.2f}, {latest['EMA50']:.2f}, {latest['EMA200']:.2f}")
    lines.append(f"RSI(14): {latest['RSI']:.2f}")
    lines.append(
        f"MACD: {latest['MACD_12_26_9']:.2f} | Signal: {latest['MACDs_12_26_9']:.2f}")
    lines.append(
        f"Bollinger Bands (20): Lower {latest['BBL_20_2.0']:.2f} | Middle {latest['BBM_20_2.0']:.2f} | Upper {latest['BBU_20_2.0']:.2f}")
    lines.append(f"Support (30d): {support:.2f} | Resistance (30d): {resistance:.2f}")

    chart_ascii = build_ascii_chart(df["close"].values)
    lines.append(f"Price Chart: {chart_ascii}")

    lines.append("\n📰 Sentiment Analysis")
    lines.append(f"Fear & Greed Index: {fear_greed} ({fng_text})")
    lines.append("Social Sentiment: 🔧 Not implemented (Twitter/Reddit API required)")
    lines.append("Whale Activity: 🔧 Not implemented (Whale Alert API required)")

    lines.append("\n🔗 On-Chain Metrics")
    lines.append("Active Addresses: 🔧 Not implemented (Glassnode)")
    lines.append("Network Fees/Revenue: 🔧 Not implemented")
    lines.append("Token Velocity: 🔧 Not implemented")

    lines.append("\n📊 Tokenomics & Fundamentals")
    lines.append("Allocation Breakdown: 🔧 Not available via free API")
    lines.append("Vesting Schedule: 🔧 Not available")
    lines.append("Emission / Inflation: 🔧 Not available")
    lines.append("Governance: 🔧 Not available")

    lines.append("⸻")
    return "\n".join(lines)


# ---------------------------------------------------
# Routes
# ---------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/analyze", methods=["POST"])
def handle_analyze():
    data = request.get_json(force=True)
    command = data.get("command", "").strip()
    if not command:
        return jsonify({"error": "No command provided."}), 400

    # Simple parsing: take last token as symbol
    symbol = command.split()[-1].upper()
    try:
        report = analyze_asset(symbol)
        return jsonify({"report": report})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)