def get_option_price(obj, symboltoken):

    ltp_data = obj.ltpData(
        exchange="NFO",
        tradingsymbol=symboltoken,
        symboltoken=symboltoken
    )

    return ltp_data["data"]["ltp"]