import sqlite3
import json
import os
import logging
import time
from typing import Optional, Tuple, Any, List

from core.db import connect_db

logger = logging.getLogger("JARVIS_BROKER")
DB_PATH = "workspace/message_broker.db"

STATUS_PENDING = "PENDING"
STATUS_IN_PROGRESS = "IN_PROGRESS"
STATUS_COMPLETED = "COMPLETED"
STATUS_FAILED = "FAILED"
STATUS_DEAD = "DEAD"

DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_LEASE_SECONDS = 120


def init_broker():
    """Event store with claim/lease/retry columns."""
    os.makedirs("workspace", exist_ok=True)
    conn = connect_db(DB_PATH)
    c = conn.cursor()
    c.execute(
        '''CREATE TABLE IF NOT EXISTS events
           (id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT,
            target_agent TEXT,
            payload TEXT,
            status TEXT DEFAULT 'PENDING',
            attempts INTEGER DEFAULT 0,
            max_attempts INTEGER DEFAULT 3,
            lease_until REAL,
            last_error TEXT,
            created_at REAL,
            updated_at REAL)'''
    )
    # Lightweight migrations for older broker DBs
    for ddl in (
        "ALTER TABLE events ADD COLUMN attempts INTEGER DEFAULT 0",
        "ALTER TABLE events ADD COLUMN max_attempts INTEGER DEFAULT 3",
        "ALTER TABLE events ADD COLUMN lease_until REAL",
        "ALTER TABLE events ADD COLUMN last_error TEXT",
        "ALTER TABLE events ADD COLUMN created_at REAL",
        "ALTER TABLE events ADD COLUMN updated_at REAL",
    ):
        try:
            c.execute(ddl)
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()


def publish_event(event_type: str, target_agent: str, payload: dict, max_attempts: int = DEFAULT_MAX_ATTEMPTS):
    init_broker()
    now = time.time()
    conn = connect_db(DB_PATH)
    c = conn.cursor()
    c.execute(
        '''INSERT INTO events
           (event_type, target_agent, payload, status, attempts, max_attempts, created_at, updated_at)
           VALUES (?, ?, ?, ?, 0, ?, ?, ?)''',
        (event_type, target_agent, json.dumps(payload, ensure_ascii=False), STATUS_PENDING, max_attempts, now, now),
    )
    event_id = c.lastrowid
    conn.commit()
    conn.close()
    logger.info(f"📬 Event Published id={event_id}: [{event_type}] for {target_agent}")
    return event_id


def reclaim_expired_leases():
    """Return expired IN_PROGRESS events to PENDING (or DEAD if attempts exhausted)."""
    init_broker()
    now = time.time()
    conn = connect_db(DB_PATH)
    c = conn.cursor()
    c.execute(
        '''SELECT id, attempts, max_attempts FROM events
           WHERE status = ? AND lease_until IS NOT NULL AND lease_until < ?''',
        (STATUS_IN_PROGRESS, now),
    )
    rows = c.fetchall()
    for event_id, attempts, max_attempts in rows:
        max_a = max_attempts or DEFAULT_MAX_ATTEMPTS
        if (attempts or 0) >= max_a:
            c.execute(
                '''UPDATE events SET status = ?, last_error = ?, updated_at = ? WHERE id = ?''',
                (STATUS_DEAD, "Lease expired after max attempts", now, event_id),
            )
            logger.error(f"☠️ Event {event_id} moved to DEAD after lease expiry")
        else:
            c.execute(
                '''UPDATE events SET status = ?, lease_until = NULL, updated_at = ?,
                   last_error = ? WHERE id = ?''',
                (STATUS_PENDING, now, "Lease expired — requeued", event_id),
            )
            logger.warning(f"♻️ Event {event_id} lease expired — requeued as PENDING")
    conn.commit()
    conn.close()


def claim_next_event(lease_seconds: int = DEFAULT_LEASE_SECONDS) -> Optional[Tuple[int, str, str, str]]:
    """
    Atomically claim one PENDING event → IN_PROGRESS with a lease.
    Returns (id, event_type, target_agent, payload_str) or None.
    """
    init_broker()
    reclaim_expired_leases()
    now = time.time()
    lease_until = now + lease_seconds
    conn = connect_db(DB_PATH)
    try:
        c = conn.cursor()
        c.execute("BEGIN IMMEDIATE")
        c.execute(
            '''SELECT id, event_type, target_agent, payload, attempts, max_attempts
               FROM events WHERE status = ? ORDER BY id ASC LIMIT 1''',
            (STATUS_PENDING,),
        )
        row = c.fetchone()
        if not row:
            conn.commit()
            return None

        event_id, event_type, target_agent, payload, attempts, max_attempts = row
        attempts = (attempts or 0) + 1
        max_a = max_attempts or DEFAULT_MAX_ATTEMPTS
        if attempts > max_a:
            c.execute(
                '''UPDATE events SET status = ?, attempts = ?, updated_at = ?, last_error = ?
                   WHERE id = ?''',
                (STATUS_DEAD, attempts, now, "Max attempts exceeded before claim", event_id),
            )
            conn.commit()
            logger.error(f"☠️ Event {event_id} dead-lettered (max attempts)")
            return None

        c.execute(
            '''UPDATE events SET status = ?, attempts = ?, lease_until = ?, updated_at = ?
               WHERE id = ? AND status = ?''',
            (STATUS_IN_PROGRESS, attempts, lease_until, now, event_id, STATUS_PENDING),
        )
        if c.rowcount != 1:
            conn.rollback()
            return None
        conn.commit()
        return (event_id, event_type, target_agent, payload)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_pending_events():
    """Legacy helper — prefer claim_next_event. Returns PENDING rows only."""
    init_broker()
    reclaim_expired_leases()
    conn = connect_db(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, event_type, target_agent, payload FROM events WHERE status = ?", (STATUS_PENDING,))
    rows = c.fetchall()
    conn.close()
    return rows


def mark_event_completed(event_id: int):
    now = time.time()
    conn = connect_db(DB_PATH)
    c = conn.cursor()
    c.execute(
        '''UPDATE events SET status = ?, lease_until = NULL, updated_at = ?, last_error = NULL
           WHERE id = ?''',
        (STATUS_COMPLETED, now, event_id),
    )
    conn.commit()
    conn.close()


def mark_event_failed(event_id: int, error: str, retry: bool = True):
    """
    On failure: requeue as PENDING if attempts remain, else DEAD.
    """
    now = time.time()
    conn = connect_db(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT attempts, max_attempts FROM events WHERE id = ?", (event_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return
    attempts, max_attempts = row
    max_a = max_attempts or DEFAULT_MAX_ATTEMPTS
    if retry and (attempts or 0) < max_a:
        status = STATUS_PENDING
    else:
        status = STATUS_DEAD
    c.execute(
        '''UPDATE events SET status = ?, lease_until = NULL, updated_at = ?, last_error = ?
           WHERE id = ?''',
        (status, now, str(error)[:2000], event_id),
    )
    conn.commit()
    conn.close()
    logger.warning(f"⚠️ Event {event_id} → {status}: {error}")


def mark_event_poison(event_id: int, error: str):
    """Malformed / non-retryable events go straight to DEAD."""
    now = time.time()
    conn = connect_db(DB_PATH)
    c = conn.cursor()
    c.execute(
        '''UPDATE events SET status = ?, lease_until = NULL, updated_at = ?, last_error = ?
           WHERE id = ?''',
        (STATUS_DEAD, now, str(error)[:2000], event_id),
    )
    conn.commit()
    conn.close()
    logger.error(f"☠️ Event {event_id} poisoned: {error}")
