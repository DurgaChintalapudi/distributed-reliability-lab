"""SQLite-backed idempotent event ledger for the synthetic inventory consumer.

SQLite transactions make the synthetic reservation and event deduplication atomic.
The Kafka offset commit is separate: replay is safe because the ledger has a
unique event_id. This is NOT distributed exactly-once delivery.
"""
import os
import sqlite3
from pathlib import Path

DB_PATH = os.getenv("INVENTORY_DB_PATH", "/data/inventory.db")


def connect(path=None):
    target = path or DB_PATH
    Path(target).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(target, timeout=10)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("CREATE TABLE IF NOT EXISTS processed_events (event_id TEXT PRIMARY KEY, order_id TEXT NOT NULL, sku TEXT NOT NULL, quantity INTEGER NOT NULL, processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
    db.commit()
    return db


def record_event(db, event):
    """Return True for first processing, False for a duplicate."""
    with db:
        cursor = db.execute(
            "INSERT OR IGNORE INTO processed_events(event_id,order_id,sku,quantity) VALUES(?,?,?,?)",
            (event["event_id"], event["order_id"], event["sku"], event["quantity"]),
        )
        return cursor.rowcount == 1
