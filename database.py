import sqlite3
import json
from config import Config

class Database:
    """SQLite database handler"""
    def __init__(self, db_file):
        self.db_file = db_file
        self.init_db()

    def init_db(self):
        """Initialize the SQLite database"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    name TEXT,
                    phones TEXT DEFAULT '[]',
                    current_phone TEXT DEFAULT '',
                    current_otp TEXT DEFAULT '',
                    approved INTEGER DEFAULT 0,
                    tokens INTEGER DEFAULT 50,
                    otp_verified_numbers TEXT DEFAULT '[]',
                    state INTEGER DEFAULT 0
                )
            ''')
            conn.commit()
        Config.log("info", "Database initialized")

    def load_users(self):
        """Load users from the database into memory with compatibility for old data"""
        users = {}
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users")
                for row in cursor.fetchall():
                    user_id, name, phones, current_phone, current_otp, approved, tokens, otp_verified_numbers, state = row
                    try:
                        phones_list = json.loads(phones) if phones else []
                    except json.JSONDecodeError:
                        Config.log("warning", f"Invalid JSON in phones for user {user_id}: {phones}. Attempting eval.")
                        phones_list = eval(phones) if phones else []
                    try:
                        otp_verified_list = json.loads(otp_verified_numbers) if otp_verified_numbers else []
                    except json.JSONDecodeError:
                        Config.log("warning", f"Invalid JSON in otp_verified_numbers for user {user_id}: {otp_verified_numbers}. Attempting eval.")
                        otp_verified_list = eval(otp_verified_numbers) if otp_verified_numbers else []

                    users[user_id] = {
                        "name": name,
                        "phones": phones_list,
                        "current_phone": current_phone,
                        "current_otp": current_otp,
                        "approved": bool(approved),
                        "tokens": tokens,
                        "otp_verified_numbers": otp_verified_list,
                        "state": state
                    }
            Config.log("info", f"Loaded {len(users)} users from database")
        except sqlite3.OperationalError as e:
            Config.log("error", f"Database error: {e}")
        return users

    def save_user(self, user_id, user_data):
        """Save or update a user's data in the database"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO users (user_id, name, phones, current_phone, current_otp, approved, tokens, otp_verified_numbers, state)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                user_data["name"],
                json.dumps(user_data["phones"]),
                user_data["current_phone"],
                user_data["current_otp"],
                int(user_data["approved"]),
                user_data["tokens"],
                json.dumps(user_data["otp_verified_numbers"]),
                user_data["state"]
            ))
            conn.commit()

    def delete_user(self, user_id):
        """Delete a user from the database"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            conn.commit()