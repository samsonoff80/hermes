"""Exact dedup через SQLite (телефон/email/сайт)"""
import re
import sqlite3
import threading
from typing import Dict

class ExactDedup:
    COMMIT_EVERY = 1000
    
    def __init__(self, db_path: str = ":memory:"):
        self.db = sqlite3.connect(db_path)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=NORMAL")
        self.db.execute("PRAGMA cache_size=10000")
        self.db.execute("CREATE TABLE IF NOT EXISTS emails (email TEXT PRIMARY KEY)")
        self.db.execute("CREATE TABLE IF NOT EXISTS pw_pairs (pair TEXT PRIMARY KEY)")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_email ON emails(email)")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_pw ON pw_pairs(pair)")
        self.db.commit()
        self._pending = 0
        self._lock = threading.Lock()
    
    def _norm_phone(self, phone: str) -> str:
        digits = re.sub(r'\D', '', (phone or ""))
        if digits.startswith("8") and len(digits) == 11:
            digits = "7" + digits[1:]
        if len(digits) > 11:
            digits = digits[-11:]
        return digits
    
    def _norm_email(self, email: str) -> str:
        return (email or "").strip().lower()
    
    def _norm_website(self, website: str) -> str:
        w = (website or "").strip().lower()
        w = re.sub(r'^https?://', '', w)
        w = re.sub(r'^www\.', '', w)
        return w.split('/')[0].split('?')[0]
    
    def is_duplicate(self, row: Dict) -> bool:
        with self._lock:
            phone = self._norm_phone(row.get("phone", ""))
            email = self._norm_email(row.get("email", ""))
            website = self._norm_website(row.get("website", ""))
            
            if email:
                cur = self.db.execute("SELECT 1 FROM emails WHERE email = ?", (email,))
                if cur.fetchone():
                    return True
            
            if phone and website:
                pw_key = f"{phone}|{website}"
                cur = self.db.execute("SELECT 1 FROM pw_pairs WHERE pair = ?", (pw_key,))
                if cur.fetchone():
                    return True
                self.db.execute("INSERT OR IGNORE INTO pw_pairs VALUES (?)", (pw_key,))
                self._pending += 1
            
            if email:
                self.db.execute("INSERT OR IGNORE INTO emails VALUES (?)", (email,))
                self._pending += 1
            
            if self._pending >= self.COMMIT_EVERY:
                self.db.commit()
                self._pending = 0
            
            return False
    
    def close(self):
        with self._lock:
            if self._pending > 0:
                self.db.commit()
            self.db.close()
