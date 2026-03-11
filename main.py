# ---------------------------------------
# IMPORT REQUIRED MODULES
# ---------------------------------------

from login import angel_login
from data_fetch import SessionExpiredError, fetch_nifty_data
from strategy import apply_indicators, check_signal
from vertex_strategy import get_vertex_signal
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
from bot_runtime import load_settings

import time
from pathlib import Path
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
LIVE_DATA_FILE = Path("live_data.csv")


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


def write_live_data(df):
    """
    Persist latest NIFTY price/indicator data for the dashboard.
    """
    if df is None or df.empty:
        return

    live_df = df[["close", "EMA9", "EMA15", "RSI"]].tail(120).copy()
    live_df.insert(0, "Index", "NIFTY")
    live_df.rename(
        columns={"close": "Price", "EMA9": "EMA9", "EMA15": "EMA15", "RSI": "RSI"},
        inplace=True,
    )
    live_df.to_csv(LIVE_DATA_FILE, index=False)


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
runtime_settings = load_settings()
if runtime_settings.get("telegram", True) and send_startup_message(
    auto_signal=runtime_settings.get("autotrade", False),
    ai_signal=runtime_settings.get("ai_strategy_enabled", False),
    bot_running=runtime_settings.get("bot_running", True),
):
    print("📩 Startup Telegram confirmation sent")
else:
    print("ℹ️ Telegram startup message skipped or failed")
print(
    f"🧠 Strategy mode: {runtime_settings.get('strategy_mode', 'manual')} | "
    f"AI enabled: {runtime_settings.get('ai_strategy_enabled', False)}"
)


def refresh_login_session():
    """Recreate the Angel session after token expiry."""
    print("🔐 Refreshing Angel One session...")
    refreshed_obj = angel_login()
    if refreshed_obj is None:
        print("❌ Session refresh failed")
        return None

    print("✅ Session refreshed")
    return refreshed_obj


# ---------------------------------------
# MAIN BOT LOOP
# ---------------------------------------

while True:
    runtime_settings = load_settings()

    if not runtime_settings.get("bot_running", True):
        print("⏸ Bot paused from dashboard. Waiting...")
        time.sleep(5)
        continue

    if not is_market_open():
        wait_until_market_open()
        continue

    wait_until_next_5min_slot()

    print("\n🔍 Checking Market Conditions...")

    # ---------------------------------------
    # FETCH NIFTY DATA
    # ---------------------------------------

    try:
        df = fetch_nifty_data(obj)
    except SessionExpiredError as exc:
        print(f"⚠️ {exc}")
        obj = refresh_login_session()
        if obj is None:
            time.sleep(30)
            continue

        try:
            df = fetch_nifty_data(obj)
        except SessionExpiredError as retry_exc:
            print(f"⚠️ Session still invalid after refresh: {retry_exc}")
            time.sleep(30)
            continue

    if df is None:

        print("⚠️ Data fetch failed")
        time.sleep(10)
        continue


    # ---------------------------------------
    # APPLY STRATEGY
    # ---------------------------------------

    df = apply_indicators(df)
    write_live_data(df)

    ai_strategy_enabled = runtime_settings.get("ai_strategy_enabled", False)
    strategy_mode = runtime_settings.get("strategy_mode", "manual")

    if ai_strategy_enabled and strategy_mode == "vertex_ai":
        signal = get_vertex_signal(df)
        if signal:
            print(
                f"🧠 Vertex AI signal: {signal.get('signal_type')} "
                f"(confidence={signal.get('confidence', 'n/a')})"
            )
        else:
            print("ℹ️ Vertex AI produced no valid signal, using manual strategy fallback")
            signal = check_signal(df)
    else:
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

            if runtime_settings.get("telegram", True):
                sent = send_premium_options(
                    "NIFTY",
                    option_type,
                    options,
                    auto_signal=runtime_settings.get("autotrade", False),
                    ai_signal=runtime_settings.get("ai_strategy_enabled", False),
                    bot_running=runtime_settings.get("bot_running", True),
                )

                if not sent:
                    print("⚠️ Failed to send Telegram message")
                    time.sleep(10)
                    continue

                print("📩 Telegram message sent")
            else:
                print("ℹ️ Telegram Alerts OFF. Skipping Telegram send.")

            if not runtime_settings.get("autotrade", False):
                print("ℹ️ Auto Trading OFF. Logging signal only.")
                log_signal(
                    "NIFTY",
                    option_type,
                    "-",
                    atm,
                    "",
                    "",
                    "",
                    rsi,
                    "SIGNAL ONLY",
                    ""
                )
                continue

            selected = None

            if runtime_settings.get("telegram", True):
                print("Waiting for telegram reply...")
                mark_telegram_updates_seen()
                valid_choices = ["1", "2", "3"]

                # ---------------------------------------
                # WAIT FOR USER SELECTION
                # ---------------------------------------

                while True:
                    latest_settings = load_settings()
                    if not latest_settings.get("bot_running", True):
                        print("⏹ Bot stopped from dashboard while waiting for reply.")
                        break

                    reply = get_telegram_reply(allowed_replies=valid_choices)

                    if reply in valid_choices:
                        selected = options[int(reply) - 1]
                        break

                    time.sleep(5)
            else:
                # Auto-select middle strike when Telegram is OFF and Auto Trade is ON.
                selected = options[1]
                print(f"🤖 Auto-selected {selected['symbol']} (middle strike)")

            if selected is None:
                continue

            # ---------------------------------------
            # CALCULATE SL / TARGET
            # ---------------------------------------

            entry = selected["price"]

            sl, tgt = calculate_sl_tgt(entry)

            print("\n✅ Option Selected:", selected["symbol"])

            print("Entry:", entry)
            print("Stop Loss:", sl)
            print("Target:", tgt)

            if runtime_settings.get("telegram", True):
                send_trade_selection(
                    selected["symbol"],
                    entry,
                    sl,
                    tgt,
                    auto_signal=runtime_settings.get("autotrade", False),
                    ai_signal=runtime_settings.get("ai_strategy_enabled", False),
                    bot_running=runtime_settings.get("bot_running", True),
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
                option_type,
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
