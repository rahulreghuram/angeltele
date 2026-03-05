# This file selects 3 strikes around ATM

def get_three_strikes(atm):

    """
    Example

    ATM = 24400

    We return:

    24350
    24400
    24450
    """

    strike1 = atm - 50
    strike2 = atm
    strike3 = atm + 50

    return [strike1, strike2, strike3]