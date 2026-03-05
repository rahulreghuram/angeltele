# Angel One NIFTY Options Bot

Python bot for:
- logging into Angel One SmartAPI
- fetching 5-minute NIFTY candles
- generating CALL/PUT signals using indicators
- finding nearby option strikes and premiums
- sending updates on Telegram
- monitoring selected trade for SL/Target outcomes

## Project Structure

- `main.py`: Main live bot loop
- `login.py`: Angel One login using API key + TOTP
- `data_fetch.py`: NIFTY 5-minute candle fetch
- `strategy.py`: Indicator and signal logic
- `token_lookup.py`: Scrip master + option token lookup
- `telegram_alert.py`: Telegram send/read utilities
- `premium_selector.py`: Strike filtering/selection
- `logger.py`: Signal/trade logging helpers
- `download_history.py`: Historical data downloader utility

## Requirements

- Python 3.10+
- Angel One SmartAPI account
- Telegram bot token + chat id

Install dependencies:

```bash
pip install smartapi-python pyotp pandas ta requests
```

## Configuration

Update `config.py` with your credentials:
- Angel One API key, client id, password, TOTP secret
- Telegram bot token and chat id

## Run

```bash
python main.py
```

## Optional Utilities

Download historical data:

```bash
python download_history.py --days 30 --interval FIVE_MINUTE --output nifty_history.csv
```

## Security Note

Do not commit live credentials. Keep secrets out of git history (prefer environment variables or a local-only config file).
