import ta


def apply_indicators(df):
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)

    df["EMA9"] = ta.trend.ema_indicator(df["close"], window=9)
    df["EMA15"] = ta.trend.ema_indicator(df["close"], window=15)
    df["RSI"] = ta.momentum.rsi(df["close"], window=14)
    # Previous 5-candle average (excluding current candle)
    df["VOL_AVG5"] = df["volume"].rolling(window=5).mean().shift(1)
    return df


def _target_from_risk(entry_price, stop_loss, signal_type):
    """
    Target points = clamp(1.5R, 20, 35)
    CALL: entry + points
    PUT:  entry - points
    """
    risk = abs(entry_price - stop_loss)
    points = min(max(1.5 * risk, 20.0), 35.0)
    if signal_type == "CALL":
        return round(entry_price + points, 2)
    return round(entry_price - points, 2)


def check_signal(df):
    """
    Returns signal dict only when all conditions are satisfied:
    symbol, entry_price, stop_loss, target, signal_type (CALL/PUT)
    """
    if len(df) < 20:
        return None

    # a: base candle, b: HH/LL candle, c: HL/LH confirmation, d: breakout candle
    a = df.iloc[-4]
    b = df.iloc[-3]
    c = df.iloc[-2]
    d = df.iloc[-1]

    # ---------- CALL (CE) ----------
    trend_up = c["close"] > c["EMA9"] and c["EMA9"] > c["EMA15"]
    hh = b["high"] > a["high"]
    hl = c["low"] > a["low"] and c["low"] < b["low"]
    rsi_ce = 52 <= c["RSI"] <= 60
    vol_ce = c["volume"] > c["VOL_AVG5"] if c["VOL_AVG5"] == c["VOL_AVG5"] else False
    ce_breakout = d["high"] > c["high"]

    if trend_up and hh and hl and rsi_ce and vol_ce and ce_breakout:
        entry_price = round(c["high"], 2)
        stop_loss = round(c["low"], 2)
        return {
            "symbol": "NIFTY",
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "target": _target_from_risk(entry_price, stop_loss, "CALL"),
            "signal_type": "CALL",
        }

    # ---------- PUT (PE) ----------
    trend_down = c["close"] < c["EMA9"] and c["EMA9"] < c["EMA15"]
    ll = b["low"] < a["low"]
    lh = c["high"] < a["high"] and c["high"] > b["high"]
    rsi_pe = 40 <= c["RSI"] <= 48
    vol_pe = c["volume"] > c["VOL_AVG5"] if c["VOL_AVG5"] == c["VOL_AVG5"] else False
    pe_breakout = d["low"] < c["low"]

    if trend_down and ll and lh and rsi_pe and vol_pe and pe_breakout:
        entry_price = round(c["low"], 2)
        stop_loss = round(c["high"], 2)
        return {
            "symbol": "NIFTY",
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "target": _target_from_risk(entry_price, stop_loss, "PUT"),
            "signal_type": "PUT",
        }

    return None
