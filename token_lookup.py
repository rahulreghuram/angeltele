import pandas as pd
import requests
import os
from datetime import datetime

SCRIP_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
SCRIP_FILE = "scrip_master.json"

def update_scrip_master():
    print("Downloading Scrip Master... (This happens once per day)")
    try:
        data = requests.get(SCRIP_URL).json()
        df = pd.DataFrame(data)
        df.to_json(SCRIP_FILE)
        return df
    except Exception as e:
        print(f"Error downloading scrip master: {e}")
        return pd.DataFrame() # Return empty DF on failure

def get_scrip_master():
    try:
        if os.path.exists(SCRIP_FILE):
            # Check if file is from today, else update
            file_time = datetime.fromtimestamp(os.path.getmtime(SCRIP_FILE))
            if file_time.date() != datetime.now().date():
                return update_scrip_master()
            return pd.read_json(SCRIP_FILE)
        else:
            return update_scrip_master()
    except Exception as e:
        print(f"Error reading scrip master: {e}")
        return pd.DataFrame()

def get_option_token(df_scrip, symbol_name, strike, option_type):
    """
    symbol_name: "NIFTY"
    strike: 24400 or 24400.0
    option_type: "CE" or "PE"
    """
    if df_scrip.empty:
        return None, None

    # Convert strike to Angel One format (multiplied by 100).
    # Example: 24400.0 -> 2440000
    try:
        strike_val = int(float(strike) * 100)
    except ValueError:
        print(f"Invalid strike price format: {strike}")
        return None, None
    
    # Filter for NIFTY Options
    # We use 'symbol' column which is formatted like 'NIFTY26MAR24400CE'
    strike_series = pd.to_numeric(df_scrip["strike"], errors="coerce")
    criteria = (df_scrip['name'] == symbol_name) & \
               (df_scrip['instrumenttype'] == 'OPTIDX') & \
               (df_scrip['symbol'].str.endswith(option_type)) & \
               (strike_series == strike_val)
               
    filtered = df_scrip[criteria].copy()

    if filtered.empty:
        return None, None

    # Sort by expiry to get the nearest one
    # Angel One expiry format is usually "26MAR2026"
    filtered['expiry_dt'] = pd.to_datetime(filtered['expiry'], format='%d%b%Y', errors='coerce')
    
    # Filter out past expiries (keep only today or future)
    today = pd.Timestamp.now().normalize()
    filtered = filtered[filtered['expiry_dt'] >= today]
    
    # Sort: Nearest expiry first
    filtered = filtered.sort_values('expiry_dt')

    if filtered.empty:
        return None, None

    # Get the nearest expiry contract
    contract = filtered.iloc[0]
    
    return contract['token'], contract['symbol']
