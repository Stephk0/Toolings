"""Log-buffer helpers for the panel log. No bpy imports.

The log lives in a scene StringProperty, so it must stay capped or it
grows without bound inside the .blend file.
"""

MAX_LOG_LINES = 200


def format_entry(message, timestamp):
    """One log line; timestamp is injected so this stays deterministic."""
    return f"[{timestamp}] {message}\n"


def append_capped(log_text, entry, max_lines=MAX_LOG_LINES):
    """Append entry to log_text, dropping the oldest lines past max_lines."""
    text = log_text + entry
    lines = text.splitlines()
    if len(lines) > max_lines:
        return "\n".join(lines[-max_lines:]) + "\n"
    return text


def tail(log_text, count):
    """Last `count` lines of the log, oldest first. Empty log -> []."""
    stripped = log_text.strip()
    if not stripped:
        return []
    lines = stripped.split('\n')
    return lines[-count:]
