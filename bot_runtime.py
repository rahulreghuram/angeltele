import json
import os
import signal
import subprocess
from pathlib import Path
from typing import Tuple

BASE_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = BASE_DIR / "bot_settings.json"
PID_FILE = BASE_DIR / "bot_process.pid"
LOG_FILE = BASE_DIR / "bot_runtime.log"
MAIN_FILE = BASE_DIR / "main.py"

DEFAULT_SETTINGS = {
    "telegram": True,
    "autotrade": False,
    "bot_running": False,
}


def load_settings() -> dict:
    """Load persistent bot settings; create defaults when file is missing/corrupt."""
    if not SETTINGS_FILE.exists():
        save_settings(DEFAULT_SETTINGS)
        return dict(DEFAULT_SETTINGS)

    try:
        data = json.loads(SETTINGS_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        save_settings(DEFAULT_SETTINGS)
        return dict(DEFAULT_SETTINGS)

    return {
        "telegram": bool(data.get("telegram", DEFAULT_SETTINGS["telegram"])),
        "autotrade": bool(data.get("autotrade", DEFAULT_SETTINGS["autotrade"])),
        "bot_running": bool(data.get("bot_running", DEFAULT_SETTINGS["bot_running"])),
    }


def save_settings(settings: dict) -> None:
    """Save dashboard settings to JSON."""
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2))


def _read_pid() -> int | None:
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text().strip())
    except (ValueError, OSError):
        return None


def _is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def bot_is_running() -> bool:
    """Check whether the managed bot process is currently alive."""
    pid = _read_pid()
    return bool(pid and _is_alive(pid))


def start_bot() -> Tuple[bool, str]:
    """Start `main.py` in background if not running."""
    if bot_is_running():
        return True, "Bot is already running."

    python_bin = Path(os.environ.get("VIRTUAL_ENV", "")) / "bin" / "python"
    if not python_bin.exists():
        python_bin = Path("python3")

    with LOG_FILE.open("a") as log_fp:
        process = subprocess.Popen(
            [str(python_bin), str(MAIN_FILE)],
            cwd=str(BASE_DIR),
            stdout=log_fp,
            stderr=log_fp,
            preexec_fn=os.setsid,
        )

    PID_FILE.write_text(str(process.pid))
    return True, f"Bot started (PID {process.pid})."


def stop_bot() -> Tuple[bool, str]:
    """Stop managed bot process if running."""
    pid = _read_pid()

    if not pid:
        return True, "Bot is already stopped."

    if not _is_alive(pid):
        PID_FILE.unlink(missing_ok=True)
        return True, "Bot was not running; cleaned stale PID."

    try:
        os.killpg(os.getpgid(pid), signal.SIGTERM)
    except ProcessLookupError:
        PID_FILE.unlink(missing_ok=True)
        return True, "Bot process already exited."
    except Exception as exc:
        return False, f"Failed to stop bot: {exc}"

    PID_FILE.unlink(missing_ok=True)
    return True, "Bot stopped."


def sync_settings_with_runtime() -> dict:
    """Ensure `bot_running` in settings reflects actual managed process state."""
    settings = load_settings()
    running = bot_is_running()
    if settings.get("bot_running") != running:
        settings["bot_running"] = running
        save_settings(settings)
    return settings
