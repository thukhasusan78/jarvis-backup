-- 001: business ledger lifecycle + jammer orders
-- Applied automatically by memory.business_storage.init_db() via CREATE/ALTER IF needed.
-- Kept here as the canonical schema document.

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id TEXT UNIQUE,
    amount TEXT,
    customer_name TEXT,
    product TEXT DEFAULT 'vip',
    status TEXT DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS jammer_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,
    jammer_model TEXT,
    customer_name TEXT,
    phone TEXT,
    city TEXT,
    address TEXT,
    payment_type TEXT,
    payment_txn_id TEXT,
    status TEXT DEFAULT 'RECORDED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
