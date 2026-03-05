def get_nearby_strikes(atm):

    strikes = [
        atm - 100,
        atm - 50,
        atm,
        atm + 50,
        atm + 100
    ]

    return strikes
