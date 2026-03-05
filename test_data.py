from data_fetch import fetch_nifty_data
from strategy import apply_indicators, check_signal
from options_logic import get_atm_strike
from telegram_alert import send_telegram_alert
import pandas as pd


if __name__ == "__main__":

    # Step 1: Fetch latest NIFTY data
    fetch_nifty_data()

    # Step 2: Load CSV
    df = pd.read_csv("nifty_5min_data.csv")

    # Step 3: Apply indicators
    df = apply_indicators(df)

    # Step 4: Check signal
    signal = check_signal(df)

    if signal:

        last_price = df.iloc[-1]["close"]
        last_rsi = df.iloc[-1]["RSI"]
        atm_strike = get_atm_strike(last_price)

        print(f"🔥 SIGNAL DETECTED: BUY {atm_strike} {signal}")

        # Send Telegram Alert
        send_telegram_alert(
            index="NIFTY",
            direction=signal,
            strike=atm_strike,
            price=last_price,
            rsi=last_rsi
        )

    else:
        print("No signal right now.")