import sqlite3
import time
import logging
from config import Config

logger = logging.getLogger("JARVIS_MEMORY")

class DatabaseManager:
    def __init__(self):
        self.db_path = Config.MEMORY_DB_PATH
        self._init_db()

    def _init_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 1. Short-term Memory (စကားဝိုင်း)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    role TEXT,
                    content TEXT,
                    timestamp REAL
                )
            ''')
            
            # 2. Long-term Memory (မင်းအကြောင်း အချက်အလက်များ)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_profile (
                    user_id INTEGER,
                    key_name TEXT,
                    value_text TEXT,
                    PRIMARY KEY (user_id, key_name)
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info(f"✅ Memory DB connected: {self.db_path}")
        except Exception as e:
            logger.error(f"❌ DB Init Error: {e}")

    # --- Short Term ---
    def add_message(self, user_id, role, content):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO chat_history (user_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (user_id, role, content, time.time())
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"❌ Save Message Error: {e}")

    def get_chat_history(self, user_id, limit=10):
        try:
            conn = sqlite3.connect(self.db_path)
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
                sender = "User" if row["role"] == "user" else "Jarvis"
                history.append(f"{sender}: {row['content']}")
            return history
        except Exception as e:
            return []

    # --- Long Term (RAM မစား၊ ထာဝရမှတ်မယ်) ---
    def update_profile(self, user_id, key, value):
        """ဥပမာ: Key='Name', Value='Mg Mg'"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO user_profile (user_id, key_name, value_text) VALUES (?, ?, ?)",
                (user_id, key, value)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"❌ Profile Update Error: {e}")
            return False

    def get_user_profile(self, user_id):
        """မင်းအကြောင်း သိသမျှ အကုန်ထုတ်ပေးမယ်"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT key_name, value_text FROM user_profile WHERE user_id = ?", (user_id,))
            rows = cursor.fetchall()
            conn.close()
            
            # Text Format နဲ့ ပြန်ပို့မယ်
            profile_text = "USER PROFILE (LONG-TERM FACTS):\n"
            if not rows:
                return profile_text + "No known facts yet."
            
            for key, val in rows:
                profile_text += f"- {key}: {val}\n"
            return profile_text
        except Exception as e:
            return "Error loading profile."
            
    def clear_history(self, user_id):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()
            return "စကားဝိုင်းမှတ်တမ်းများကို ရှင်းလင်းလိုက်ပါပြီ (Profile အချက်အလက်များ ကျန်ရှိနေမည်)။"
        except Exception as e:
            return "Error clearing history."

db_manager = DatabaseManager()