import sqlite3, hashlib, json, time, logging
from pathlib import Path

logger = logging.getLogger("consilium.cache")

class SemanticCache:
    def __init__(self):
        self.db = Path.home() / ".hermes/cache/semantic.db"
        self.db.parent.mkdir(parents=True, exist_ok=True)
        self.threshold = 0.85
        with sqlite3.connect(str(self.db)) as c:
            c.execute("CREATE TABLE IF NOT EXISTS cache (id INTEGER PRIMARY KEY, hash TEXT UNIQUE, query TEXT, response TEXT, model TEXT, tokens INTEGER, hits INTEGER DEFAULT 1)")
    
    def get(self, query: str) -> dict | None:
        words = set(query.lower().split())
        if not words: return None
        with sqlite3.connect(str(self.db)) as c:
            for row in c.execute("SELECT query, response, model, tokens FROM cache").fetchall():
                cw = set(row[0].lower().split())
                if cw:
                    sim = len(words & cw) / len(words | cw)
                    if sim > self.threshold:
                        c.execute("UPDATE cache SET hits = hits + 1 WHERE query = ?", (row[0],))
                        return {"response": json.loads(row[1]), "model": row[2], "tokens_saved": row[3], "similarity": sim}
        return None
    
    def set(self, query: str, response: dict, model: str, tokens: int):
        with sqlite3.connect(str(self.db)) as c:
            c.execute("INSERT OR REPLACE INTO cache VALUES (NULL, ?, ?, ?, ?, ?, 1)", (hashlib.sha256(query.encode()).hexdigest(), query, json.dumps(response), model, tokens))

semantic_cache = SemanticCache()
