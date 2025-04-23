
from keep_alive import keep_alive
keep_alive()

import time
import pytz
import pandas as pd
import requests
from datetime import datetime
from telegram import Bot, ParseMode
from telegram.error import TelegramError

TOKEN = "7534683921:AAHVRAJpK6_gA-48kAcD_dz8ChYFeaaEF8o"
CHAT_ID = "923087333"
bot = Bot(token=TOKEN)

SYMBOL = "BTCUSDT"
INTERVAL = "15m"
LIMIT = 100

def get_klines(symbol=SYMBOL, interval=INTERVAL, limit=LIMIT):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    data = requests.get(url).json()
    df = pd.DataFrame(data, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "number_of_trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ])
    df["close"] = df["close"].astype(float)
    return df

def calculate_indicators(df):
    df["ema_9"] = df["close"].ewm(span=9).mean()
    df["ema_21"] = df["close"].ewm(span=21).mean()
    df["rsi"] = 100 - (100 / (1 + df["close"].pct_change().rolling(14).mean()))
    df["macd"] = df["close"].ewm(span=12).mean() - df["close"].ewm(span=26).mean()
    df["macd_signal"] = df["macd"].ewm(span=9).mean()
    df["adx"] = df["close"].diff().abs().rolling(14).mean()
    return df

def calculate_score(row):
    score = 0
    if row["rsi"] < 30: score += 2
    elif row["rsi"] > 70: score += 2
    if row["ema_9"] > row["ema_21"]: score += 2
    elif row["ema_9"] < row["ema_21"]: score += 2
    if row["macd"] > row["macd_signal"]: score += 2
    elif row["macd"] < row["macd_signal"]: score += 2
    if row["adx"] > 1.5: score += 2
    return score

def get_time():
    turkey_time = datetime.now(pytz.timezone("Europe/Istanbul"))
    return turkey_time.strftime("%d.%m.%Y • %H:%M")

def send_signal(signal, price, score):
    zaman = get_time()
    tp = [round(price * (1 + i*0.005), 2) for i in range(1, 6)]
    msg = f"📊 *Ultra Ultimate 3.2 Sinyali*\n\n"           f"*Coin:* {SYMBOL}\n*Yön:* {signal}\n*Skor:* {score}/10\n*Giriş:* {price}\n" +           ''.join([f"*TP{i+1}:* {tp[i]}\n" for i in range(5)]) + f"*Zaman:* {zaman}"
    sent = bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode=ParseMode.MARKDOWN)
    return sent.message_id, tp

def update_message(message_id, price, tps, signal, score):
    check = ["⬜"]*5
    for i, tp in enumerate(tps):
        if (signal == "LONG" and price >= tp) or (signal == "SHORT" and price <= tp):
            check[i] = "✅"
    zaman = get_time()
    new_text = f"📊 *Ultra Ultimate 3.2 Sinyali*\n\n*Coin:* {SYMBOL}\n*Yön:* {signal}\n*Skor:* {score}/10\n" +                f"*Fiyat:* {price}\n" + ''.join([f"{check[i]} TP{i+1}: {tps[i]}\n" for i in range(5)]) + f"*Zaman:* {zaman}"
    try:
        bot.edit_message_text(chat_id=CHAT_ID, message_id=message_id, text=new_text, parse_mode=ParseMode.MARKDOWN)
    except TelegramError as e:
        print("Güncelleme hatası:", e)

def run_bot():
    while True:
        df = get_klines()
        df = calculate_indicators(df)
        row = df.iloc[-1]
        score = calculate_score(row)
        price = row["close"]
        if score >= 8:
            signal = "LONG" if row["ema_9"] > row["ema_21"] else "SHORT"
            msg_id, tps = send_signal(signal, price, score)
            for _ in range(30):
                price = get_klines().iloc[-1]["close"]
                update_message(msg_id, price, tps, signal, score)
                time.sleep(60)
        time.sleep(60)
run_bot()
