"""Jarvis' Gedächtnis: welche Mails schon bearbeitet wurden und was heute passiert ist."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path


class State:
    def __init__(self, path: Path):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS processed (
                key TEXT PRIMARY KEY,
                day TEXT NOT NULL,
                account TEXT, sender TEXT, subject TEXT,
                category TEXT, summary TEXT, action TEXT
            );
            CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT);
            CREATE TABLE IF NOT EXISTS pending_calls (id INTEGER PRIMARY KEY, text TEXT);
        """)
        self.db.commit()

    # -- Mails --------------------------------------------------------------
    def is_processed(self, key: str) -> bool:
        return self.db.execute("SELECT 1 FROM processed WHERE key=?", (key,)).fetchone() is not None

    def record(self, key: str, day: date, account: str, sender: str, subject: str,
               category: str, summary: str, action: str) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO processed VALUES (?,?,?,?,?,?,?,?)",
            (key, day.isoformat(), account, sender, subject, category, summary, action))
        self.db.commit()

    def day_entries(self, day: date) -> list[sqlite3.Row]:
        return self.db.execute(
            "SELECT * FROM processed WHERE day=? ORDER BY rowid", (day.isoformat(),)).fetchall()

    # -- Einstellungen / Merker ---------------------------------------------
    def get(self, k: str) -> str | None:
        row = self.db.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
        return row["v"] if row else None

    def set(self, k: str, v: str) -> None:
        self.db.execute("INSERT OR REPLACE INTO kv VALUES (?,?)", (k, v))
        self.db.commit()

    def first_start(self) -> datetime | None:
        value = self.get("first_start")
        return datetime.fromisoformat(value) if value else None

    # -- Anrufe in der Ruhezeit ---------------------------------------------
    def queue_call(self, text: str) -> None:
        self.db.execute("INSERT INTO pending_calls (text) VALUES (?)", (text,))
        self.db.commit()

    def take_pending_calls(self) -> list[str]:
        rows = self.db.execute("SELECT id, text FROM pending_calls ORDER BY id").fetchall()
        self.db.execute("DELETE FROM pending_calls")
        self.db.commit()
        return [r["text"] for r in rows]
