import signal
import time

from bot_runtime import bot_is_running, load_settings, start_bot, stop_bot, sync_settings_with_runtime

POLL_SECONDS = 5
_running = True


def _handle_signal(signum, frame):
    global _running
    _running = False


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)

print("[bot-daemon] started")

while _running:
    try:
        settings = sync_settings_with_runtime()
        desired_running = bool(settings.get("bot_running", False))
        actual_running = bot_is_running()

        if desired_running and not actual_running:
            ok, msg = start_bot()
            print(f"[bot-daemon] start requested -> {msg}")
        elif not desired_running and actual_running:
            ok, msg = stop_bot()
            print(f"[bot-daemon] stop requested -> {msg}")
    except Exception as exc:
        print(f"[bot-daemon] error: {exc}")

    time.sleep(POLL_SECONDS)

# On service shutdown, stop managed bot process for clean exit.
if bot_is_running():
    ok, msg = stop_bot()
    print(f"[bot-daemon] shutdown -> {msg}")

print("[bot-daemon] stopped")
