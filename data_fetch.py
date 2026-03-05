import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TIMEFRAME_INTERVAL = "FIVE_MINUTE"
IST = ZoneInfo("Asia/Kolkata")


def fetch_nifty_data(obj):

    # Date range (last 5 days)
    to_date = datetime.now(IST)
    from_date = to_date - timedelta(days=5)

    historicParam = {
        "exchange": "NSE",
        "symboltoken": "99926000",   # NIFTY spot
        "interval": TIMEFRAME_INTERVAL,
        "fromdate": from_date.strftime("%Y-%m-%d %H:%M"),
        "todate": to_date.strftime("%Y-%m-%d %H:%M")
    }

    print("Fetching NIFTY data...")

    response = obj.getCandleData(historicParam)

    if response['status'] == False:
        print("Error fetching data:", response)
        return None

    data = response['data']

    df = pd.DataFrame(data, columns=[
        "datetime",
        "open",
        "high",
        "low",
        "close",
        "volume"
    ])

    # Convert datetime column
    df["datetime"] = pd.to_datetime(df["datetime"])

    # Save to CSV
    df.to_csv("nifty_5min_data.csv", index=False)

    print("Data saved as nifty_5min_data.csv ✅")
    print(df.tail())

    return df
