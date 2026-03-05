# ---------------------------------------
# IMPORT REQUIRED MODULES
# ---------------------------------------

from login import angel_login
from data_fetch import fetch_nifty_data
from strategy import apply_indicators, check_signal
from options_logic import get_atm_strike
from token_lookup import get_scrip_master, get_option_token
from telegram_alert import (
    send_premium_options,
    get_telegram_reply,
    mark_telegram_updates_seen,
    send_trade_selection,
    send_startup_message
)
from premium_selector import get_three_strikes
from logger import log_signal

import time
from datetime import datetime, timedelta, time as dt_time
from zoneinfo import ZoneInfo


# ---------------------------------------
# STOP LOSS / TARGET SETTINGS
# ---------------------------------------

SL_PERCENT = 0.10
TGT_PERCENT = 0.20
MONITOR_INTERVAL_SEC = 5
MONITOR_TIMEOUT_SEC = 60 * 30
IST = ZoneInfo("Asia/Kolkata")
MARKET_OPEN_TIME = dt_time(9, 15)
MARKET_CLOSE_TIME = dt_time(15, 30)


def calculate_sl_tgt(price):
    """
    Calculate Stop Loss and Target
    """

    sl = round(price * (1 - SL_PERCENT), 2)
    tgt = round(price * (1 + TGT_PERCENT), 2)

    return sl, tgt


def now_ist():
    return datetime.now(IST)


def is_market_open(now=None):
    if now is None:
        now = now_ist()

    if now.weekday() >= 5:  # Saturday/Sunday
        return False

    current_time = now.time()
    return MARKET_OPEN_TIME <= current_time <= MARKET_CLOSE_TIME


def get_next_market_open(now=None):
    if now is None:
        now = now_ist()

    if now.weekday() >= 5:
        days_to_monday = 7 - now.weekday()
        next_open = (now + timedelta(days=days_to_monday)).replace(
            hour=MARKET_OPEN_TIME.hour,
            minute=MARKET_OPEN_TIME.minute,
            second=0,
            microsecond=0,
        )
    elif now.time() < MARKET_OPEN_TIME:
        next_open = now.replace(
            hour=MARKET_OPEN_TIME.hour,
            minute=MARKET_OPEN_TIME.minute,
            second=0,
            microsecond=0,
        )
    else:
        next_open = (now + timedelta(days=1)).replace(
            hour=MARKET_OPEN_TIME.hour,
            minute=MARKET_OPEN_TIME.minute,
            second=0,
            microsecond=0,
        )

    while next_open.weekday() >= 5:
        next_open += timedelta(days=1)

    return next_open


def wait_until_market_open():
    now = now_ist()
    next_open = get_next_market_open(now)
    sleep_seconds = (next_open - now).total_seconds()

    if sleep_seconds > 0:
        print(
            f"⏸ Market closed (IST {now.strftime('%Y-%m-%d %H:%M:%S')}). "
            f"Sleeping until IST {next_open.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        time.sleep(sleep_seconds)


# ---------------------------------------
# GET OPTION PREMIUM
# ---------------------------------------

def get_option_price(obj, token, symbol):
    """
    Fetch option premium (LTP)
    """

    try:

        data = obj.ltpData(
            exchange="NFO",
            tradingsymbol=symbol,
            symboltoken=token
        )

        return data["data"]["ltp"]

    except:

        return None


def monitor_trade(obj, token, symbol, sl, tgt):
    """
    Monitor selected option premium and return final outcome.
    """
    print("📈 Monitoring selected option for SL/TGT...")
    start_ts = time.time()
    last_price = None

    while time.time() - start_ts <= MONITOR_TIMEOUT_SEC:
        if not is_market_open():
            return "MARKET CLOSED", last_price

        current_price = get_option_price(obj, token, symbol)

        if current_price is None:
            time.sleep(MONITOR_INTERVAL_SEC)
            continue

        last_price = current_price
        print(f"LTP: {current_price} | SL: {sl} | TGT: {tgt}")

        if current_price <= sl:
            return "SL HIT", current_price
        if current_price >= tgt:
            return "TGT HIT", current_price

        time.sleep(MONITOR_INTERVAL_SEC)

    return "NOT HIT (TIMEOUT)", last_price


def wait_until_next_5min_slot():
    """
    Sleep until the next exact 5-minute boundary (e.g. 09:15, 09:20).
    """
    now = now_ist()
    next_block_minute = ((now.minute // 5) + 1) * 5

    if next_block_minute >= 60:
        next_run = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        next_run = now.replace(minute=next_block_minute, second=0, microsecond=0)

    if next_run.time() > MARKET_CLOSE_TIME:
        wait_until_market_open()
        return

    sleep_seconds = (next_run - now).total_seconds()
    if sleep_seconds > 0:
        print(f"⏱ Waiting for next fetch at IST {next_run.strftime('%H:%M:%S')}")
        time.sleep(sleep_seconds)


# ---------------------------------------
# START BOT
# ---------------------------------------

print("🚀 NIFTY OPTIONS BOT STARTED")


# ---------------------------------------
# LOGIN TO ANGEL ONE
# ---------------------------------------

obj = angel_login()

if obj is None:

    print("❌ Login Failed")
    exit()


# ---------------------------------------
# LOAD SCRIP MASTER DATABASE
# ---------------------------------------

scrip_db = get_scrip_master()

print("✅ Scrip Master Loaded")
if send_startup_message():
    print("📩 Startup Telegram confirmation sent")
else:
    print("⚠️ Startup Telegram confirmation failed")


# ---------------------------------------
# MAIN BOT LOOP
# ---------------------------------------

while True:
    if not is_market_open():
        wait_until_market_open()
        continue

    wait_until_next_5min_slot()

    print("\n🔍 Checking Market Conditions...")

    # ---------------------------------------
    # FETCH NIFTY DATA
    # ---------------------------------------

    df = fetch_nifty_data(obj)

    if df is None:

        print("⚠️ Data fetch failed")
        time.sleep(10)
        continue


    # ---------------------------------------
    # APPLY STRATEGY
    # ---------------------------------------

    df = apply_indicators(df)

    signal = check_signal(df)


    # ---------------------------------------
    # IF SIGNAL FOUND
    # ---------------------------------------

    if signal:

        print("🚀 Signal detected:", signal)

        spot = df.iloc[-1]["close"]

        rsi = df.iloc[-1]["RSI"]

        atm = get_atm_strike(spot)
        option_type = "CE" if signal["signal_type"] == "CALL" else "PE"

        print("ATM Strike:", atm)


        # ---------------------------------------
        # FIND 3 STRIKES AROUND ATM
        # ---------------------------------------

        strikes = get_three_strikes(atm)

        options = []


        # ---------------------------------------
        # FETCH PREMIUM FOR EACH STRIKE
        # ---------------------------------------

        for strike in strikes:

            token, symbol = get_option_token(
                scrip_db,
                "NIFTY",
                strike,
                option_type
            )

            if token:

                premium = get_option_price(obj, token, symbol)

                if premium:

                    options.append({
                        "symbol": symbol,
                        "price": premium,
                        "strike": strike,
                        "token": token
                    })


        # ---------------------------------------
        # SEND TELEGRAM MESSAGE
        # ---------------------------------------

        if len(options) == 3:
            options = sorted(options, key=lambda x: x["strike"])
            print(
                "Options prepared:",
                [(o["strike"], o["price"], o["symbol"]) for o in options]
            )

            sent = send_premium_options(
                "NIFTY",
                option_type,
                options
            )

            if not sent:
                print("⚠️ Failed to send Telegram message")
                time.sleep(10)
                continue

            print("📩 Telegram message sent")

            print("Waiting for telegram reply...")
            mark_telegram_updates_seen()

            valid_choices = ["1", "2", "3"]


            # ---------------------------------------
            # WAIT FOR USER SELECTION
            # ---------------------------------------

            while True:

                reply = get_telegram_reply(allowed_replies=valid_choices)

                if reply in valid_choices:

                    selected = options[int(reply) - 1]

                    break

                time.sleep(5)

            # ---------------------------------------
            # CALCULATE SL / TARGET
            # ---------------------------------------

            entry = selected["price"]

            sl, tgt = calculate_sl_tgt(entry)

            print("\n✅ Option Selected:", selected["symbol"])

            print("Entry:", entry)
            print("Stop Loss:", sl)
            print("Target:", tgt)

            send_trade_selection(
                selected["symbol"],
                entry,
                sl,
                tgt
            )


            # ---------------------------------------
            # MONITOR TRADE
            # ---------------------------------------

            status, exit_price = monitor_trade(
                obj,
                selected["token"],
                selected["symbol"],
                sl,
                tgt
            )
            print(f"📌 Trade Result: {status} | Exit Price: {exit_price}")


            # ---------------------------------------
            # LOG SIGNAL
            # ---------------------------------------
            log_signal(
                "NIFTY",
                signal["signal_type"],
                selected["symbol"],
                selected["strike"],
                entry,
                sl,
                tgt,
                rsi,
                status,
                exit_price
            )

            print("📁 Signal Logged")


        else:
            print("⚠️ Could not fetch all 3 nearby ATM option premiums")


    else:

        print("No signal detected")
