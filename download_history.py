import argparse
import time
from datetime import datetime, timedelta

import pandas as pd

from login import angel_login


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download Angel One historical 5-minute candle data for a full year."
    )
    parser.add_argument("--year", type=int, default=2024, help="Year to download, e.g. 2024")
    parser.add_argument("--exchange", default="NSE", help="Exchange code, e.g. NSE")
    parser.add_argument("--symboltoken", default="99926000", help="Instrument symbol token")
    parser.add_argument("--interval", default="FIVE_MINUTE", help="Candle interval")
    parser.add_argument("--chunk-days", type=int, default=20, help="Days per API request")
    parser.add_argument("--sleep", type=float, default=1.5, help="Delay between requests")
    parser.add_argument(
        "--output",
        default=None,
        help="Output CSV file path (default: data_<symboltoken>_<year>_5min.csv)",
    )
    return parser.parse_args()


def request_chunk(obj, params, retries=5, base_sleep=2.0):
    for attempt in range(1, retries + 1):
        resp = obj.getCandleData(params)
        if resp and resp.get("status"):
            return resp
        err = (resp or {}).get("errorcode", "")
        msg = (resp or {}).get("message", "")
        print(f"  request failed (attempt {attempt}/{retries}): {msg} {err}".strip())
        if err == "AB1004" or "TooManyRequests" in msg:
            time.sleep(base_sleep * attempt)
            continue
        time.sleep(base_sleep)
    return resp


def main():
    args = parse_args()
    obj = angel_login()
    if not obj:
        raise SystemExit("Login failed")

    start = datetime(args.year, 1, 1, 0, 0)
    end = datetime(args.year + 1, 1, 1, 0, 0)
    step = timedelta(days=args.chunk_days)
    rows = []

    while start < end:
        to_dt = min(start + step, end)
        params = {
            "exchange": args.exchange,
            "symboltoken": args.symboltoken,
            "interval": args.interval,
            "fromdate": start.strftime("%Y-%m-%d %H:%M"),
            "todate": to_dt.strftime("%Y-%m-%d %H:%M"),
        }

        print(f"Downloading {params['fromdate']} -> {params['todate']}")
        data = request_chunk(obj, params)

        if data and data.get("status") and data.get("data"):
            rows.extend(data["data"])
            print(f"  rows fetched: {len(data['data'])}")
        else:
            print(f"  skipping chunk, final response: {data}")

        start = to_dt
        time.sleep(args.sleep)

    if not rows:
        raise SystemExit("No rows downloaded.")

    # Deduplicate by timestamp and sort chronologically.
    by_ts = {}
    for row in rows:
        by_ts[row[0]] = row
    unique_rows = [by_ts[ts] for ts in sorted(by_ts.keys())]

    df = pd.DataFrame(unique_rows, columns=["datetime", "open", "high", "low", "close", "volume"])
    output = args.output or f"data_{args.symboltoken}_{args.year}_5min.csv"
    df.to_csv(output, index=False)
    print(f"Saved {len(df)} rows -> {output}")


if __name__ == "__main__":
    main()
