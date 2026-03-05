import csv
import os
from datetime import datetime

FILE_NAME = "signals_log.csv"

def log_signal(index, direction, symbol, strike, entry_price, sl, tgt, rsi, status, exit_price):

    file_exists = os.path.isfile(FILE_NAME)

    with open(FILE_NAME, "a", newline="") as file:
        writer = csv.writer(file)

        # If file not exists, write header first
        if not file_exists:
            writer.writerow([
                "Date",
                "Time",
                "Index",
                "Direction",
                "Symbol",
                "Strike",
                "Entry Option Price",
                "SL",
                "TGT",
                "Exit Price",
                "RSI",
                "Status"
            ])

        writer.writerow([
            datetime.now().date(),
            datetime.now().strftime("%H:%M:%S"),
            index,
            direction,
            symbol,
            strike,
            entry_price,
            sl,
            tgt,
            exit_price,
            rsi,
            status
        ])
