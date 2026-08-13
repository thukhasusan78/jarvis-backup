-- 002: message broker claim / lease / retry columns
-- Applied automatically by core.message_broker.init_broker().

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT,
    target_agent TEXT,
    payload TEXT,
    status TEXT DEFAULT 'PENDING',
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    lease_until REAL,
    last_error TEXT,
    created_at REAL,
    updated_at REAL
);
