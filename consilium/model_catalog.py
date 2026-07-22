#!/usr/bin/env python3
"""Model Catalog — кэш моделей в SQLite с автообновлением."""
import sqlite3, time, logging
from pathlib import Path

logger = logging.getLogger("consilium.catalog")
DB_PATH = Path(__file__).parent / "model_catalog.db"

class ModelCatalog:
    def __init__(self):
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS models (
                provider TEXT, model TEXT, context INTEGER,
                tags TEXT, updated REAL, PRIMARY KEY (provider, model))""")
            conn.commit()
    
    def update(self, provider, models):
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.execute("DELETE FROM models WHERE provider=?", (provider,))
            for m in models:
                conn.execute("INSERT INTO models VALUES (?,?,?,?,?)",
                    (provider, m.get("id",""), m.get("context_length",0),
                     ",".join(m.get("tags",[])), time.time()))
            conn.commit()
        logger.info(f"📋 {provider}: {len(models)} models cached")
    
    def get_models(self, provider=None):
        with sqlite3.connect(str(DB_PATH)) as conn:
            if provider:
                return conn.execute("SELECT * FROM models WHERE provider=?", (provider,)).fetchall()
            return conn.execute("SELECT * FROM models").fetchall()

catalog = ModelCatalog()
