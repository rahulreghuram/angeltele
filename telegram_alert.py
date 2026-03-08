import requests
from config import BOT_TOKEN, CHAT_ID

API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"
LAST_UPDATE_ID = None


def _status_lines(auto_signal=None, ai_signal=None, bot_running=None):
    lines = []
    if auto_signal is not None:
        lines.append(f"Auto Signal: {'ON' if auto_signal else 'OFF'}")
    if ai_signal is not None:
        lines.append(f"AI Signal: {'ON' if ai_signal else 'OFF'}")
    if bot_running is not None:
        lines.append(f"Bot Status: {'ON' if bot_running else 'OFF'}")
    return lines


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

def send_premium_options(
    index,
    direction,
    options,
    auto_signal=None,
    ai_signal=None,
    bot_running=None
):

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
    status_lines = _status_lines(auto_signal, ai_signal, bot_running)
    if status_lines:
        lines.append("")
        lines.extend(status_lines)
    message = "\n".join(lines)

    ok, _ = _post(
        "sendMessage",
        {
            "chat_id": CHAT_ID,
            "text": message
        }
    )
    return ok


def send_telegram_alert(
    index,
    direction,
    strike,
    price,
    rsi,
    auto_signal=None,
    ai_signal=None,
    bot_running=None
):
    """
    Backward-compatible single alert sender.
    """
    lines = [
        "OPTION ALERT",
        "",
        f"Index: {index}",
        f"Direction: {direction}",
        f"Strike: {strike}",
        f"Price: {price}",
        f"RSI: {rsi}",
    ]
    status_lines = _status_lines(auto_signal, ai_signal, bot_running)
    if status_lines:
        lines.extend(status_lines)
    message = "\n".join(lines)
    ok, _ = _post(
        "sendMessage",
        {
            "chat_id": CHAT_ID,
            "text": message
        }
    )
    return ok


def send_trade_selection(
    symbol,
    entry,
    sl,
    tgt,
    auto_signal=None,
    ai_signal=None,
    bot_running=None
):
    """
    Send selected trade details to Telegram.
    """
    lines = [
        f"Option Selected: {symbol}",
        f"Entry: {entry}",
        f"Stop Loss: {sl}",
        f"Target: {tgt}",
    ]
    status_lines = _status_lines(auto_signal, ai_signal, bot_running)
    if status_lines:
        lines.extend(status_lines)
    message = "\n".join(lines)
    ok, _ = _post(
        "sendMessage",
        {
            "chat_id": CHAT_ID,
            "text": message
        }
    )
    return ok


def send_startup_message(auto_signal=None, ai_signal=None, bot_running=None):
    """
    Send startup ping to confirm bot is connected.
    """
    lines = ["Bot connected and running. Monitoring NIFTY strategy now."]
    status_lines = _status_lines(auto_signal, ai_signal, bot_running)
    if status_lines:
        lines.extend([""] + status_lines)
    message = "\n".join(lines)
    ok, _ = _post(
        "sendMessage",
        {
            "chat_id": CHAT_ID,
            "text": message
        }
    )
    return ok


def send_bot_status_message(bot_running, auto_signal=None, ai_signal=None):
    """
    Send bot ON/OFF status update to Telegram.
    """
    lines = [f"Bot is now {'ON' if bot_running else 'OFF'}."]
    status_lines = _status_lines(auto_signal, ai_signal, bot_running)
    if status_lines:
        lines.extend([""] + status_lines)
    message = "\n".join(lines)
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
