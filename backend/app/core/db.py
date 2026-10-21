import sqlite3
from contextlib import contextmanager
from ..core.config import settings


@contextmanager
def connection():
    db = sqlite3.connect(settings.database_path, timeout=30)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA foreign_keys=ON")
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def initialize():
    with connection() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS captures (
          id INTEGER PRIMARY KEY, captured_at TEXT NOT NULL, image_path TEXT,
          image BLOB, image_hash TEXT NOT NULL, process_name TEXT NOT NULL DEFAULT '',
          window_title TEXT NOT NULL DEFAULT '', ocr_text TEXT NOT NULL DEFAULT '', embedding BLOB,
          ocr_blocks TEXT NOT NULL DEFAULT '[]'
        );
        CREATE INDEX IF NOT EXISTS idx_captures_time ON captures(captured_at DESC);
        CREATE INDEX IF NOT EXISTS idx_captures_process ON captures(process_name);
        CREATE TABLE IF NOT EXISTS ignored_processes (process_name TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE VIRTUAL TABLE IF NOT EXISTS captures_fts USING fts5(ocr_text, window_title, process_name, content='captures', content_rowid='id');
        CREATE TRIGGER IF NOT EXISTS captures_ai AFTER INSERT ON captures BEGIN
          INSERT INTO captures_fts(rowid, ocr_text, window_title, process_name) VALUES (new.id, new.ocr_text, new.window_title, new.process_name);
        END;
        CREATE TRIGGER IF NOT EXISTS captures_ad AFTER DELETE ON captures BEGIN
          INSERT INTO captures_fts(captures_fts, rowid, ocr_text, window_title, process_name) VALUES('delete', old.id, old.ocr_text, old.window_title, old.process_name);
        END;
        CREATE TRIGGER IF NOT EXISTS captures_au AFTER UPDATE ON captures BEGIN
          INSERT INTO captures_fts(captures_fts, rowid, ocr_text, window_title, process_name) VALUES('delete', old.id, old.ocr_text, old.window_title, old.process_name);
          INSERT INTO captures_fts(rowid, ocr_text, window_title, process_name) VALUES (new.id, new.ocr_text, new.window_title, new.process_name);
        END;
        """)
        # Migrate databases created by earlier builds.
        columns = {row[1] for row in db.execute("PRAGMA table_info(captures)")}
        if "image_path" not in columns:
            db.execute("ALTER TABLE captures ADD COLUMN image_path TEXT")
        if "ocr_blocks" not in columns:
            db.execute("ALTER TABLE captures ADD COLUMN ocr_blocks TEXT NOT NULL DEFAULT '[]'")
        db.execute("INSERT INTO captures_fts(captures_fts) VALUES('rebuild')")


def read_setting(key: str, default: str) -> str:
    with connection() as db:
        row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row[0] if row else default


def write_setting(key: str, value: str):
    with connection() as db:
        db.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
