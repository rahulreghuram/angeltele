import requests
from config import BOT_TOKEN, CHAT_ID

API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"
LAST_UPDATE_ID = None


def _post(method, payload):
    try:
        response = requests.post(
            f"{API_BASE}/{method}",
            data=payload,
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        return bool(data.get("ok")), data
    except Exception as e:
        print(f"Telegram POST error: {e}")
        return False, {}


def _get_updates(offset=None):
    params = {}
    if offset is not None:
        params["offset"] = offset
    try:
        response = requests.get(
            f"{API_BASE}/getUpdates",
            params=params,
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        if data.get("ok"):
            return data.get("result", [])
        return []
    except Exception as e:
        print(f"Telegram GET error: {e}")
        return []


def mark_telegram_updates_seen():
    """
    Move cursor to latest update so old replies are ignored.
    """
    global LAST_UPDATE_ID
    updates = _get_updates()
    if updates:
        LAST_UPDATE_ID = updates[-1]["update_id"] + 1


# -----------------------------
# SEND OPTION CHOICES
# -----------------------------

def send_premium_options(index, direction, options):

    """
    Sends 3 option premiums to telegram
    """

    option_choices = options[:3]
    if len(option_choices) != 3:
        return False

    lines = [
        "SIGNAL DETECTED",
        "",
        f"Index: {index}",
        f"Direction: {direction}",
        "",
        "3 Nearby ATM strikes:",
        "",
    ]

    for i, item in enumerate(option_choices, start=1):
        lines.append(
            f"{i}. Strike {item['strike']} | Premium Rs {item['price']} | {item['symbol']}"
        )

    lines.append("")
    lines.append("Which premium do you want to buy?")
    lines.append("Reply: 1 / 2 / 3")
    message = "\n".join(lines)

    ok, _ = _post(
        "sendMessage",
        {
            "chat_id": CHAT_ID,
            "text": message
        }
    )
    return ok


def send_telegram_alert(index, direction, strike, price, rsi):
    """
    Backward-compatible single alert sender.
    """
    message = (
        "OPTION ALERT\n\n"
        f"Index: {index}\n"
        f"Direction: {direction}\n"
        f"Strike: {strike}\n"
        f"Price: {price}\n"
        f"RSI: {rsi}"
    )
    ok, _ = _post(
        "sendMessage",
        {
            "chat_id": CHAT_ID,
            "text": message
        }
    )
    return ok


def send_trade_selection(symbol, entry, sl, tgt):
    """
    Send selected trade details to Telegram.
    """
    message = (
        f"Option Selected: {symbol}\n"
        f"Entry: {entry}\n"
        f"Stop Loss: {sl}\n"
        f"Target: {tgt}"
    )
    ok, _ = _post(
        "sendMessage",
        {
            "chat_id": CHAT_ID,
            "text": message
        }
    )
    return ok


def send_startup_message():
    """
    Send startup ping to confirm bot is connected.
    """
    message = "Bot connected and running. Monitoring NIFTY strategy now."
    ok, _ = _post(
        "sendMessage",
        {
            "chat_id": CHAT_ID,
            "text": message
        }
    )
    return ok


# -----------------------------
# READ TELEGRAM REPLY
# -----------------------------

def get_telegram_reply(allowed_replies=None):

    """
    Reads new user replies from configured Telegram chat.
    """
    global LAST_UPDATE_ID

    updates = _get_updates(offset=LAST_UPDATE_ID)

    if not updates:
        return None

    if LAST_UPDATE_ID is None:
        LAST_UPDATE_ID = updates[0]["update_id"]

    for update in updates:
        LAST_UPDATE_ID = update["update_id"] + 1

        message = update.get("message", {})
        text = message.get("text")
        chat = message.get("chat", {})
        sender = message.get("from", {})

        if str(chat.get("id")) != str(CHAT_ID):
            continue
        if sender.get("is_bot"):
            continue
        if not text:
            continue

        text = text.strip()
        if allowed_replies and text not in allowed_replies:
            continue
        return text

    return None
