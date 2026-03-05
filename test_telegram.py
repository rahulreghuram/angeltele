from telegram_alert import send_telegram_alert

send_telegram_alert(
    index="NIFTY",
    direction="CE",
    strike=25000,
    price=24980,
    rsi=62.5
)

print("Test message sent.")