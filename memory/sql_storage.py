import sqlite3
import time
import logging
import os
from config import Config
from core.db import connect_db

logger = logging.getLogger("JARVIS_SQL_STORAGE")

class SQLStorage:
    def __init__(self):
        self.db_path = Config.MEMORY_DB_PATH
        # DB ဖိုင် မရှိရင် အလိုအလျောက် ဆောက်ပေးရန်
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _connect(self):
        return connect_db(self.db_path)

    def _init_db(self):
        try:
            conn = self._connect()
            cursor = conn.cursor()
            
            # ၁။ Short-term Memory (စကားဝိုင်း မှတ်တမ်း)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    role TEXT,
                    content TEXT,
                    timestamp REAL
                )
            ''')
            
            # ၂။ Permanent Knowledge (Sir အကြောင်း အချက်အလက်များ)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_profile (
                    user_id INTEGER,
                    key_name TEXT,
                    value_text TEXT,
                    PRIMARY KEY (user_id, key_name)
                )
            ''')

            # ၃။ Ongoing Tasks (လက်ရှိ လုပ်လက်စ အလုပ်များကို သီးသန့်မှတ်ရန် - အသစ်)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ongoing_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    task_description TEXT,
                    status TEXT,
                    timestamp REAL
                )
            ''')

            cursor.execute('''CREATE TABLE IF NOT EXISTS secretary_state (
                            key TEXT PRIMARY KEY,
                            value TEXT NOT NULL)''')
            
            conn.commit()
            conn.close()
            logger.info(f"✅ SQL Storage (Layer 1) Initialized.")
        except Exception as e:
            logger.error(f"❌ SQL DB Init Error: {e}")

    # ==========================================
    # အပိုင်း (က) - စကားဝိုင်း မှတ်တမ်း (Chat History)
    # ==========================================
    def add_message(self, user_id, role, content):
        try:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO chat_history (user_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (user_id, role, content, time.time())
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Save Message Error: {e}")

    def get_chat_history(self, user_id, limit=10):
        try:
            conn = self._connect()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, content FROM chat_history WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, limit)
            )
            rows = cursor.fetchall()
            conn.close()
            history = []
            for row in reversed(rows):
                sender = "Sir" if row["role"] == "user" else "Jarvis"
                history.append(f"{sender}: {row['content']}")
            return history
        except Exception as e:
            return []

    def clear_history(self, user_id):
        try:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()
            return "စကားဝိုင်းမှတ်တမ်းများကို ရှင်းလင်းလိုက်ပါပြီ။"
        except Exception as e:
            return "Error clearing history."

    # ==========================================
    # အပိုင်း (ခ) - ထာဝရ မှတ်ဉာဏ် (Permanent Knowledge)
    # ==========================================
    def update_profile(self, user_id, key, value):
        try:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO user_profile (user_id, key_name, value_text) VALUES (?, ?, ?)",
                (user_id, key, value)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Profile Update Error: {e}")
            return False

    def get_user_profile(self, user_id):
        try:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute("SELECT key_name, value_text FROM user_profile WHERE user_id = ?", (user_id,))
            rows = cursor.fetchall()
            conn.close()
            
            profile_text = "USER PROFILE (PERMANENT KNOWLEDGE):\n"
            if not rows:
                return profile_text + "No known facts yet."
            
            for key, val in rows:
                profile_text += f"- {key}: {val}\n"
            return profile_text
        except Exception as e:
            return "Error loading profile."

    # ==========================================
    # အပိုင်း (ဂ) - လုပ်လက်စ အလုပ်များ (Ongoing Tasks) [NEW FEATURE]
    # ==========================================
    def add_ongoing_task(self, user_id, task_description):
        """အလုပ်တစ်ခု စလုပ်တိုင်း ဒီမှာ လာမှတ်ထားမယ်"""
        try:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO ongoing_tasks (user_id, task_description, status, timestamp) VALUES (?, ?, ?, ?)",
                (user_id, task_description, "In Progress", time.time())
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Add Task Error: {e}")
            return False

    def get_ongoing_tasks(self, user_id):
        """လက်ရှိ ဘာအလုပ်တွေ တန်းလန်းဖြစ်နေလဲ ပြန်ဆွဲထုတ်မယ်"""
        try:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute("SELECT id, task_description, status FROM ongoing_tasks WHERE user_id = ?", (user_id,))
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                return ""
            
            tasks_text = "CURRENT ONGOING TASKS:\n"
            for row_id, desc, status in rows:
                tasks_text += f"- [Task ID: {row_id}] {desc} (Status: {status})\n"
            return tasks_text
        except Exception as e:
            return ""

    def remove_ongoing_task(self, task_id):
        """အလုပ်ပြီးသွားရင် ပြန်ဖျက်မယ်"""
        try:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM ongoing_tasks WHERE id = ?", (task_id,))
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    # ==========================================
    # VIP Mute State (Secretary)
    # ==========================================
    def get_vip_mute_until(self, user_id: int) -> float:
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM secretary_state WHERE key = ?", (f"vip_mute_{user_id}",))
        row = cursor.fetchone()
        conn.close()
        return float(row[0]) if row else 0.0

    def set_vip_mute_until(self, user_id: int, timestamp: float):
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO secretary_state (key, value) VALUES (?, ?)", (f"vip_mute_{user_id}", str(timestamp)))
        conn.commit()
        conn.close()
        
    def get_vip_timestamps(self, user_id: int) -> list:
        import json
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM secretary_state WHERE key = ?", (f"vip_timestamps_{user_id}",))
        row = cursor.fetchone()
        conn.close()
        return json.loads(row[0]) if row else []

    def set_vip_timestamps(self, user_id: int, timestamps: list):
        import json
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO secretary_state (key, value) VALUES (?, ?)", (f"vip_timestamps_{user_id}", json.dumps(timestamps)))
        conn.commit()
        conn.close()

    # ==========================================
    # Vision Quota (Gemini Vision Analysis Limit per Customer)
    # ==========================================
    def get_vision_timestamps(self, user_id: int) -> list:
        """Customer တစ်ယောက်ရဲ့ နောက်ဆုံး ၂၄ နာရီအတွင်း Vision Analyze လုပ်ခဲ့တဲ့ အချိန်များ"""
        import json
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM secretary_state WHERE key = ?", (f"vision_ts_{user_id}",))
        row = cursor.fetchone()
        conn.close()
        return json.loads(row[0]) if row else []

    def set_vision_timestamps(self, user_id: int, timestamps: list):
        import json
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO secretary_state (key, value) VALUES (?, ?)", (f"vision_ts_{user_id}", json.dumps(timestamps)))
        conn.commit()
        conn.close()

    # ==========================================
    # Persisted Secretary runtime state
    # ==========================================
    def get_last_image(self, chat_id: int):
        """Return (path, timestamp) or None."""
        import json
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM secretary_state WHERE key = ?", (f"last_image_{chat_id}",))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        try:
            data = json.loads(row[0])
            return data.get("path"), float(data.get("ts", 0))
        except Exception:
            return None

    def set_last_image(self, chat_id: int, path: str, ts: float = None):
        import json
        conn = self._connect()
        cursor = conn.cursor()
        payload = json.dumps({"path": path, "ts": ts if ts is not None else time.time()})
        cursor.execute(
            "INSERT OR REPLACE INTO secretary_state (key, value) VALUES (?, ?)",
            (f"last_image_{chat_id}", payload),
        )
        conn.commit()
        conn.close()

    def clear_last_image(self, chat_id: int):
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM secretary_state WHERE key = ?", (f"last_image_{chat_id}",))
        conn.commit()
        conn.close()

    def get_human_active_until(self, chat_id: int) -> float:
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM secretary_state WHERE key = ?", (f"human_active_{chat_id}",))
        row = cursor.fetchone()
        conn.close()
        return float(row[0]) if row else 0.0

    def set_human_active(self, chat_id: int, timestamp: float = None):
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO secretary_state (key, value) VALUES (?, ?)",
            (f"human_active_{chat_id}", str(timestamp if timestamp is not None else time.time())),
        )
        conn.commit()
        conn.close()


sql_storage = SQLStorage()