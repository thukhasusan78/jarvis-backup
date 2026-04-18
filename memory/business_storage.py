import sqlite3
import os
import logging

logger = logging.getLogger("BUSINESS_STORAGE")
DB_PATH = "workspace/business_ledger.db"

def init_db():
    """Business သီးသန့် Database တည်ဆောက်ခြင်း"""
    os.makedirs("workspace", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Transaction ID ကို UNIQUE (ထပ်ခွင့်မရှိ) အဖြစ် သတ်မှတ်ထားသည်
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  transaction_id TEXT UNIQUE,
                  amount TEXT,
                  customer_name TEXT,
                  status TEXT DEFAULT 'PENDING',
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def is_transaction_exists(transaction_id: str) -> bool:
    """ဒီ ပြေစာ ID က အရင်က သုံးပြီးသားလား စစ်ဆေးခြင်း (Anti-Replay)"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM transactions WHERE transaction_id = ?", (transaction_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

def record_transaction(transaction_id: str, amount: str, customer_name: str, status: str = 'VERIFIED') -> bool:
    """ပြေစာအသစ်ဖြစ်ပါက Ledger ထဲသို့ မှတ်တမ်းတင်ခြင်း"""
    init_db()
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO transactions (transaction_id, amount, customer_name, status) VALUES (?, ?, ?, ?)",
                  (transaction_id, amount, customer_name, status))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False # ID ထပ်နေလျှင် False ပြန်ပေးမည်
    except Exception as e:
        logger.error(f"Business DB Error: {e}")
        return False