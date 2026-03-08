# Angel One NIFTY Options Bot

Python bot for:
- logging into Angel One SmartAPI
- fetching 5-minute NIFTY candles
- generating CALL/PUT signals using indicators
- switching between manual strategy and Vertex AI strategy
- finding nearby option strikes and premiums
- sending updates on Telegram
- monitoring selected trade for SL/Target outcomes

## Project Structure

- `main.py`: Main live bot loop
- `login.py`: Angel One login using API key + TOTP
- `data_fetch.py`: NIFTY 5-minute candle fetch
- `strategy.py`: Indicator and signal logic
- `vertex_strategy.py`: Vertex AI based signal logic (with safe fallback)
- `token_lookup.py`: Scrip master + option token lookup
- `telegram_alert.py`: Telegram send/read utilities
- `premium_selector.py`: Strike filtering/selection
- `logger.py`: Signal/trade logging helpers
- `download_history.py`: Historical data downloader utility
- `dashboard.py`: Streamlit dashboard for bot controls and strategy toggles

## Requirements

- Python 3.10+
- Angel One SmartAPI account
- Telegram bot token + chat id

Install dependencies:

```bash
pip install smartapi-python pyotp pandas ta requests
```

For Vertex AI strategy support, install:

```bash
pip install google-cloud-aiplatform
```

## Configuration

Update `config.py` with your credentials:
- Angel One API key, client id, password, TOTP secret
- Telegram bot token and chat id

For Vertex AI mode, set environment variables:

```bash
export VERTEX_PROJECT_ID="your-gcp-project-id"
export VERTEX_LOCATION="us-central1"
export VERTEX_MODEL="gemini-1.5-flash-002"
export VERTEX_MIN_CONFIDENCE="0.55"
```

## Run

```bash
python main.py
```

Run dashboard:

```bash
streamlit run dashboard.py --server.address 127.0.0.1 --server.port 8501
```

## Strategy Control (Dashboard)

- `AI Strategy (ON/OFF)`: enable or disable AI signal generation
- `Strategy Mode`:
  - `manual`: use local indicator strategy from `strategy.py`
  - `vertex_ai`: use Vertex AI signal path from `vertex_strategy.py`
- If Vertex AI is unavailable, invalid, or low confidence, bot falls back to manual strategy for that cycle.

## Optional Utilities

Download historical data:

```bash
python download_history.py --days 30 --interval FIVE_MINUTE --output nifty_history.csv
```

## Security Note

Do not commit live credentials. Keep secrets out of git history (prefer environment variables or a local-only config file).
