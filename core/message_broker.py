import sqlite3
import json
import os
import logging

logger = logging.getLogger("JARVIS_BROKER")
DB_PATH = "workspace/message_broker.db"

def init_broker():
    """Event များကို သိမ်းဆည်းရန် Database တည်ဆောက်ခြင်း"""
    os.makedirs("workspace", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS events
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  event_type TEXT,
                  target_agent TEXT,
                  payload TEXT,
                  status TEXT DEFAULT 'PENDING')''')
    conn.commit()
    conn.close()

def publish_event(event_type: str, target_agent: str, payload: dict):
    """Agent များက အလုပ်ပြီးလျှင် Event လွှင့်ရန်"""
    init_broker()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO events (event_type, target_agent, payload) VALUES (?, ?, ?)",
              (event_type, target_agent, json.dumps(payload)))
    conn.commit()
    conn.close()
    logger.info(f"📬 Event Published: [{event_type}] for {target_agent}")

def get_pending_events():
    """Orchestrator မှ အလုပ်မလုပ်ရသေးသော Event များကို ဆွဲယူရန်"""
    init_broker()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, event_type, target_agent, payload FROM events WHERE status = 'PENDING'")
    rows = c.fetchall()
    conn.close()
    return rows

def mark_event_completed(event_id: int):
    """Orchestrator မှ အလုပ်လုပ်ပြီးပါက ပိတ်သိမ်းရန်"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE events SET status = 'COMPLETED' WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()