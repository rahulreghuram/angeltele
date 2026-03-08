import time
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from bot_runtime import (
    bot_is_running,
    save_settings,
    start_bot,
    stop_bot,
    sync_settings_with_runtime,
)


# -----------------------------
# File paths and constants
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent
LIVE_DATA_FILE = BASE_DIR / "live_data.csv"
SIGNALS_FILE = BASE_DIR / "signals_log.csv"
DEFAULT_PASSWORD = "bot123"
REFRESH_SECONDS = 5


# -----------------------------
# Utility functions
# -----------------------------
def safe_rerun() -> None:
    """Use experimental rerun when available, else fallback to stable rerun."""
    rerun_fn = getattr(st, "experimental_rerun", None)
    if callable(rerun_fn):
        rerun_fn()
    else:
        st.rerun()


def load_live_data() -> pd.DataFrame:
    """Load live market data from CSV and normalize expected numeric columns."""
    expected_cols = ["Index", "Price", "EMA9", "EMA15", "RSI"]

    if not LIVE_DATA_FILE.exists():
        return pd.DataFrame(columns=expected_cols)

    try:
        df = pd.read_csv(LIVE_DATA_FILE)
    except Exception:
        return pd.DataFrame(columns=expected_cols)

    for col in expected_cols:
        if col not in df.columns:
            df[col] = pd.NA

    for col in ["Price", "EMA9", "EMA15", "RSI"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df[expected_cols]


def load_signals() -> pd.DataFrame:
    """Load signal history from CSV with expected columns."""
    expected_cols = [
        "Date",
        "Time",
        "Index",
        "Direction",
        "Strike",
        "Entry Price",
        "RSI",
        "Status",
    ]

    if not SIGNALS_FILE.exists():
        return pd.DataFrame(columns=expected_cols)

    try:
        df = pd.read_csv(SIGNALS_FILE)
    except Exception:
        return pd.DataFrame(columns=expected_cols)

    for col in expected_cols:
        if col not in df.columns:
            df[col] = pd.NA

    return df[expected_cols].tail(20)


def status_badge(label: str, is_on: bool, on_text: str = "ON", off_text: str = "OFF") -> str:
    """Return HTML for a colored status indicator."""
    dot_class = "dot-on" if is_on else "dot-off"
    value = on_text if is_on else off_text
    return f"<div class='status-item'><span class='dot {dot_class}'></span><b>{label}</b>: {value}</div>"


# -----------------------------
# Streamlit page setup
# -----------------------------
st.set_page_config(page_title="Angel Bot Dashboard", layout="wide")

# Custom CSS for trading terminal look and feel.
st.markdown(
    """
    <style>
    .stApp {
        background: radial-gradient(circle at top right, #1b2430 0%, #0e1117 45%, #0b0f14 100%);
        color: #e8eef7;
    }
    .panel {
        border: 1px solid #273349;
        border-radius: 12px;
        padding: 12px;
        background: rgba(20, 28, 40, 0.75);
        box-shadow: 0 4px 12px rgba(0,0,0,0.25);
    }
    .status-wrap {
        display: grid;
        gap: 8px;
    }
    .status-item {
        font-size: 0.95rem;
        background: rgba(255,255,255,0.03);
        border: 1px solid #273349;
        border-radius: 8px;
        padding: 8px 10px;
    }
    .dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 999px;
        margin-right: 8px;
    }
    .dot-on { background: #10b981; box-shadow: 0 0 8px #10b981; }
    .dot-off { background: #ef4444; box-shadow: 0 0 8px #ef4444; }
    .safety-note {
        margin-top: 8px;
        padding: 10px;
        border-left: 4px solid #f59e0b;
        background: rgba(245, 158, 11, 0.12);
        border-radius: 6px;
        font-size: 0.9rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Login state management
# -----------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

st.title("Angel Bot Trading Terminal")

if not st.session_state.authenticated:
    st.subheader("Login")
    password = st.text_input("Enter password", type="password")

    if st.button("Login", type="primary"):
        if password == DEFAULT_PASSWORD:
            st.session_state.authenticated = True
            st.success("Login successful.")
            safe_rerun()
        else:
            st.error("Incorrect password. Please try again.")

    # Auto refresh loop (required): keeps login page aligned with app refresh behavior.
    time.sleep(REFRESH_SECONDS)
    safe_rerun()


# -----------------------------
# Authenticated dashboard
# -----------------------------
settings = sync_settings_with_runtime()
live_df = load_live_data()
signals_df = load_signals()

# Top row: Bot Status | Controls
left_top, right_top = st.columns([1, 1])

with left_top:
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    st.subheader("Bot Status")

    st.markdown("<div class='status-wrap'>", unsafe_allow_html=True)
    st.markdown(
        status_badge(
            "Bot Running",
            settings["bot_running"],
            on_text="RUNNING",
            off_text="STOPPED",
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        status_badge("Telegram Alerts", settings["telegram"]),
        unsafe_allow_html=True,
    )
    st.markdown(
        status_badge("Auto Trade", settings["autotrade"]),
        unsafe_allow_html=True,
    )
    st.markdown(
        status_badge("AI Strategy", settings.get("ai_strategy_enabled", False)),
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='status-item'><b>Strategy Mode</b>: {settings.get('strategy_mode', 'manual')}</div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # Safety rule panel to make behavior explicit.
    st.markdown(
        "<div class='safety-note'><b>Safety:</b> This dashboard does not place real trades. "
        "It only controls bot process state, reads CSV data, and updates <code>bot_settings.json</code>.</div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

with right_top:
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    st.subheader("Bot Control Panel")

    # Toggle controls for bot behavior.
    telegram = st.toggle("Telegram Alerts", value=settings["telegram"])
    autotrade = st.toggle("Auto Trading", value=settings["autotrade"])
    ai_strategy_enabled = st.toggle(
        "AI Strategy (ON/OFF)",
        value=settings.get("ai_strategy_enabled", False),
    )
    strategy_mode = st.selectbox(
        "Strategy Mode",
        options=["manual", "vertex_ai"],
        index=0 if settings.get("strategy_mode", "manual") == "manual" else 1,
    )
    bot_running = st.toggle("Bot Status (RUNNING/STOPPED)", value=settings["bot_running"])

    updated_settings = {
        "telegram": telegram,
        "autotrade": autotrade,
        "ai_strategy_enabled": ai_strategy_enabled,
        "strategy_mode": strategy_mode,
        "bot_running": bot_running,
    }

    # Persist settings and apply runtime bot start/stop on toggle changes.
    if updated_settings != settings:
        if updated_settings["bot_running"] != settings["bot_running"]:
            if updated_settings["bot_running"]:
                ok, msg = start_bot()
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
            else:
                ok, msg = stop_bot()
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

            updated_settings["bot_running"] = bot_is_running()

        save_settings(updated_settings)
        st.success("Settings synced to bot_settings.json")
        settings = updated_settings
        safe_rerun()

    # Logout button clears authentication state.
    if st.button("Logout"):
        st.session_state.authenticated = False
        safe_rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# Middle row: Live Price Metrics
st.markdown("### Live Price Metrics")
metrics_col1, metrics_col2, metrics_col3 = st.columns(3)

if live_df.empty:
    with metrics_col1:
        st.metric("NIFTY Price", "N/A")
    with metrics_col2:
        st.metric("EMA Trend", "N/A")
    with metrics_col3:
        st.metric("RSI Value", "N/A")
else:
    nifty_row = live_df.iloc[0]

    price_val = nifty_row["Price"]
    ema9_val = nifty_row["EMA9"]
    ema15_val = nifty_row["EMA15"]
    rsi_val = nifty_row["RSI"]

    if pd.notna(ema9_val) and pd.notna(ema15_val):
        ema_trend = "Bullish" if ema9_val > ema15_val else "Bearish"
    else:
        ema_trend = "N/A"

    with metrics_col1:
        st.metric("NIFTY Price", f"{price_val:.2f}" if pd.notna(price_val) else "N/A")
    with metrics_col2:
        st.metric("EMA Trend", ema_trend)
    with metrics_col3:
        st.metric("RSI Value", f"{rsi_val:.2f}" if pd.notna(rsi_val) else "N/A")

st.dataframe(live_df, use_container_width=True)


# Bottom row: Chart | Signal History
chart_col, signal_col = st.columns([1.4, 1])

with chart_col:
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    st.subheader("Live Price Chart")

    # Plotly line chart for Price, EMA9, and EMA15.
    fig = go.Figure()

    if not live_df.empty:
        x_axis = list(range(1, len(live_df) + 1))
        fig.add_trace(go.Scatter(x=x_axis, y=live_df["Price"], mode="lines", name="Price"))
        fig.add_trace(go.Scatter(x=x_axis, y=live_df["EMA9"], mode="lines", name="EMA9"))
        fig.add_trace(go.Scatter(x=x_axis, y=live_df["EMA15"], mode="lines", name="EMA15"))

    fig.update_layout(
        template="plotly_dark",
        height=360,
        xaxis_title="Ticks",
        yaxis_title="Value",
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", y=1.1, x=0),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with signal_col:
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    st.subheader("Signal History (Last 20)")

    # Style CE rows green and PE rows red.
    def highlight_direction(row: pd.Series):
        direction = str(row.get("Direction", "")).upper()
        if "CE" in direction:
            return ["background-color: rgba(16,185,129,0.20)"] * len(row)
        if "PE" in direction:
            return ["background-color: rgba(239,68,68,0.20)"] * len(row)
        return [""] * len(row)

    if signals_df.empty:
        st.info("No signal data found in signals_log.csv")
    else:
        styled_signals = signals_df.style.apply(highlight_direction, axis=1)
        st.dataframe(styled_signals, use_container_width=True, height=360)

    st.markdown("</div>", unsafe_allow_html=True)


# -----------------------------
# Auto refresh (required)
# -----------------------------
st.caption(f"Auto-refresh every {REFRESH_SECONDS} seconds")
time.sleep(REFRESH_SECONDS)
safe_rerun()
