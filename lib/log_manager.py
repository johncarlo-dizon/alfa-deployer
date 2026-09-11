import os
from datetime import datetime

from config import LOGS_FILE


def append_full_log(text):
    """Append a timestamped line to the persistent detailed log file.
    Best-effort — a logging hiccup should never interrupt a deployment."""
    try:
        with open(LOGS_FILE, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {text}\n")
    except Exception:
        pass


def read_full_log():
    if os.path.exists(LOGS_FILE):
        try:
            with open(LOGS_FILE, "r", encoding="utf-8") as f:
                content = f.read()
            return content if content.strip() else "(No logs recorded yet.)"
        except Exception:
            return "(Could not read log file.)"
    return "(No logs recorded yet.)"


def clear_full_log():
    try:
        if os.path.exists(LOGS_FILE):
            os.remove(LOGS_FILE)
        return True
    except Exception:
        return False
