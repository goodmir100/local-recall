from ..core.db import connection

DEFAULT_IGNORED = {"1password.exe", "keepass.exe", "keepassxc.exe"}

def get_ignored():
    with connection() as db:
        return sorted(DEFAULT_IGNORED | {row[0].lower() for row in db.execute("SELECT process_name FROM ignored_processes")})

def is_ignored(process_name: str, window_title: str = "") -> bool:
    if process_name.lower() in set(get_ignored()): return True
    browser = process_name.lower() in {"chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe"}
    sensitive_words = ("online banking", "internet banking", "bank account", "payment details", "checkout payment")
    title = window_title.lower()
    return browser and any(word in title for word in sensitive_words)

def update_ignored(processes: list[str]):
    with connection() as db:
        db.execute("DELETE FROM ignored_processes")
        db.executemany("INSERT OR IGNORE INTO ignored_processes(process_name) VALUES(?)", [(p.strip().lower(),) for p in processes if p.strip()])
