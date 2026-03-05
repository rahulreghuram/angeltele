def get_atm_strike(index_price):
    return round(index_price / 50) * 50

def calculate_sl_tgt(entry_price, risk_reward_ratio=2, stop_loss_pct=0.10):
    """
    Calculates SL and TGT based on percentage.
    Default: 10% SL, 20% Target.
    """
    sl = entry_price * (1 - stop_loss_pct)
    tgt = entry_price * (1 + (stop_loss_pct * risk_reward_ratio))
    
    return round(sl, 2), round(tgt, 2)