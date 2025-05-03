import requests
import time
import datetime
import pytz
import logging
from telegram import Bot

# ======================= CONFIG =======================
TELEGRAM_TOKEN = "<INSERISCI_IL_TUO_TOKEN>"
TELEGRAM_CHAT_ID = "<INSERISCI_IL_TUO_CHAT_ID>"

COINBASE_URL = "https://api.exchange.coinbase.com/products"
ALERT_THRESHOLD_PERCENT = 4.0
MONITOR_INTERVAL_MINUTES = 5
TIMEZONE = "CET"
VOLUME_LOOKBACK_HOURS = 24

# ======================= LOGGER =======================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ======================= TELEGRAM =======================
bot = Bot(token=TELEGRAM_TOKEN)

def send_telegram_alert(message):
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as e:
        logger.error(f"Errore nell'invio del messaggio Telegram: {e}")

# ======================= METODI =======================
def get_coinbase_tickers():
    try:
        response = requests.get(COINBASE_URL)
        response.raise_for_status()
        return [item['id'] for item in response.json() if item['quote_currency'] == 'USD']
    except Exception as e:
        logger.error(f"Errore nel recupero tickers Coinbase: {e}")
        return []

def get_current_price(product_id):
    try:
        url = f"{COINBASE_URL}/{product_id}/ticker"
        response = requests.get(url)
        return float(response.json()['price'])
    except:
        return None

def get_historic_data(product_id, granularity):
    end = datetime.datetime.utcnow()
    start = end - datetime.timedelta(minutes=granularity * 2)
    url = f"{COINBASE_URL}/{product_id}/candles?start={start.isoformat()}&end={end.isoformat()}&granularity={granularity * 60}"
    try:
        response = requests.get(url)
        return response.json()
    except:
        return []

def get_price_change(product_id):
    candles = get_historic_data(product_id, 10)
    if not candles or len(candles) < 2:
        return None
    latest = candles[0][4]
    old = candles[-1][4]
    change = ((latest - old) / old) * 100
    return round(change, 2), latest

def get_volume_spike(product_id):
    candles = get_historic_data(product_id, 60)  # 1h
    if not candles or len(candles) < 6:
        return False
    volumes = [c[5] for c in candles]
    avg_volume = sum(volumes[:-1]) / (len(volumes) - 1)
    return volumes[-1] > avg_volume * 1.5

def get_social_mentions(coin):
    # Placeholder: da integrare con scraping API gratuite (Reddit, X, ecc.)
    return "📣 menzioni social in aumento"

def estimate_reliability(product_id):
    if product_id.endswith("-USD"):
        coin = product_id.replace("-USD", "")
    else:
        coin = product_id
    market_cap_placeholder = 100_000_000  # Da collegare a CoinGecko
    ranking_placeholder = 150
    if market_cap_placeholder > 100_000_000 and ranking_placeholder < 150:
        return "✅ alta affidabilità"
    else:
        return "⚠️ rischio elevato"

def monitor():
    tickers = get_coinbase_tickers()
    for ticker in tickers:
        result = get_price_change(ticker)
        if not result:
            continue
        change, current_price = result

        if abs(change) >= ALERT_THRESHOLD_PERCENT and get_volume_spike(ticker):
            reliability = estimate_reliability(ticker)
            social = get_social_mentions(ticker)
            direction = "🔼" if change > 0 else "🔻"
            timestamp = datetime.datetime.now(pytz.timezone(TIMEZONE)).strftime("%H:%M")
            message = f"{direction} {timestamp} - {ticker} ha avuto una variazione del {change}% negli ultimi 10 minuti.\nPrezzo attuale: {current_price} USD\n{social} | {reliability}"
            send_telegram_alert(message)

# ======================= LOOP =======================
while True:
    try:
        monitor()
        time.sleep(MONITOR_INTERVAL_MINUTES * 60)
    except Exception as e:
        logger.error(f"Errore nel ciclo di monitoraggio: {e}")
        time.sleep(60)
