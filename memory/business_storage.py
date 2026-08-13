import sqlite3
import os
import logging
from typing import Optional, Dict, Any, List

from core.db import connect_db, db_connection

logger = logging.getLogger("BUSINESS_STORAGE")
DB_PATH = "workspace/business_ledger.db"

# Payment lifecycle: PENDING (reserved) → VERIFIED (checks passed) → FULFILLED | FAILED
STATUS_PENDING = "PENDING"
STATUS_VERIFIED = "VERIFIED"
STATUS_FULFILLED = "FULFILLED"
STATUS_FAILED = "FAILED"


def init_db():
    os.makedirs("workspace", exist_ok=True)
    conn = connect_db(DB_PATH)
    c = conn.cursor()
    c.execute(
        '''CREATE TABLE IF NOT EXISTS transactions
           (id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT UNIQUE,
            amount TEXT,
            customer_name TEXT,
            product TEXT DEFAULT 'vip',
            status TEXT DEFAULT 'PENDING',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)'''
    )
    c.execute(
        '''CREATE TABLE IF NOT EXISTS jammer_orders
           (id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            jammer_model TEXT,
            customer_name TEXT,
            phone TEXT,
            city TEXT,
            address TEXT,
            payment_type TEXT,
            payment_txn_id TEXT,
            status TEXT DEFAULT 'RECORDED',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)'''
    )
    # Lightweight migrations for older DBs
    for ddl in (
        "ALTER TABLE transactions ADD COLUMN product TEXT DEFAULT 'vip'",
        "ALTER TABLE transactions ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    ):
        try:
            c.execute(ddl)
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()


def is_transaction_exists(transaction_id: str) -> bool:
    init_db()
    with db_connection(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM transactions WHERE transaction_id = ?", (transaction_id,))
        return c.fetchone() is not None


def get_transaction(transaction_id: str) -> Optional[Dict[str, Any]]:
    init_db()
    with db_connection(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM transactions WHERE transaction_id = ?", (transaction_id,))
        row = c.fetchone()
        return dict(row) if row else None


def record_transaction(
    transaction_id: str,
    amount: str,
    customer_name: str,
    status: str = STATUS_VERIFIED,
    product: str = "vip",
) -> bool:
    """Insert a new ledger row. Returns False on duplicate (IntegrityError)."""
    init_db()
    try:
        with db_connection(DB_PATH) as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO transactions (transaction_id, amount, customer_name, status, product) VALUES (?, ?, ?, ?, ?)",
                (transaction_id, amount, customer_name, status, product),
            )
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        logger.error(f"Business DB Error: {e}")
        return False


def update_transaction_status(transaction_id: str, status: str) -> bool:
    init_db()
    with db_connection(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE transactions SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE transaction_id = ?",
            (status, transaction_id),
        )
        return c.rowcount > 0


def mark_fulfilled(transaction_id: str) -> bool:
    return update_transaction_status(transaction_id, STATUS_FULFILLED)


def mark_failed(transaction_id: str) -> bool:
    return update_transaction_status(transaction_id, STATUS_FAILED)


def record_jammer_order_row(
    chat_id: int,
    jammer_model: str,
    customer_name: str,
    phone: str,
    city: str,
    address: str,
    payment_type: str,
    payment_txn_id: str = "",
    status: str = "RECORDED",
) -> int:
    init_db()
    with db_connection(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            '''INSERT INTO jammer_orders
               (chat_id, jammer_model, customer_name, phone, city, address, payment_type, payment_txn_id, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (chat_id, jammer_model, customer_name, phone, city, address, payment_type, payment_txn_id, status),
        )
        return c.lastrowid


def list_recent_jammer_orders(limit: int = 20) -> List[Dict[str, Any]]:
    init_db()
    with db_connection(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM jammer_orders ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in c.fetchall()]
