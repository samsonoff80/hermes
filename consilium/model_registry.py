#!/usr/bin/env python3
"""Model Registry — классификация и отбор моделей под задачи."""
import sqlite3, time, logging
from pathlib import Path

logger = logging.getLogger("consilium.registry")

DB_PATH = Path(__file__).parent / "model_registry.db"

# Минимальные требования к моделям
REQUIREMENTS = {
    "context_length": {
        "chat": 128000,
        "code": 128000,
        "search": 128000,
        "analysis": 500000,
    },
    "free_tokens_daily_min": 100000,
}

# Ключевые слова для классификации
TAG_KEYWORDS = {
    "chat": ["llama", "mistral", "gpt", "gemma", "qwen", "hermes", "openai"],
    "code": ["coder", "deepseek", "code", "hy3"],
    "search": ["gemini", "scout", "sonnet", "llama", "gpt", "mistral", "qwen"],
    "analysis": ["large", "ultra", "r1"],
}

# Модели которые НЕ подходят ни под какую задачу
EXCLUDE_KEYWORDS = [
    "embed", "audio", "speech", "vision", "guard", "safety",
    "bge", "pipecat", "tts", "asr", "whisper", "stable-diffusion"
]

class ModelRegistry:
    def __init__(self):
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS models (
                provider TEXT,
                model TEXT,
                context_length INTEGER DEFAULT 0,
                free_tokens_daily INTEGER DEFAULT 0,
                tags TEXT DEFAULT '',
                priority REAL DEFAULT 50.0,
                enabled INTEGER DEFAULT 1,
                added_at REAL,
                last_checked REAL,
                PRIMARY KEY (provider, model))""")
            conn.commit()

    def classify_model(self, model_name: str) -> list:
        """Определяет теги модели по ключевым словам."""
        name_lower = model_name.lower()
        
        # Проверяем исключения
        if any(kw in name_lower for kw in EXCLUDE_KEYWORDS):
            return []
        
        tags = []
        for tag, keywords in TAG_KEYWORDS.items():
            if any(kw in name_lower for kw in keywords):
                tags.append(tag)
        
        return tags if tags else ["chat"]  # по умолчанию — chat

    def should_enable(self, context_length: int, tags: list, free_tokens: int) -> bool:
        """Проверяет, подходит ли модель под наши требования (per-tag пороги)."""
        if not tags:
            return False
        for tag in tags:
            required = REQUIREMENTS["context_length"].get(tag, 128000)
            if context_length >= required:
                if free_tokens > 0 and free_tokens < REQUIREMENTS["free_tokens_daily_min"]:
                    continue
                return True
        return False

    def update_model(self, provider: str, model: str, context_length: int, free_tokens: int = 0):
        """Добавляет или обновляет модель в реестре."""
        tags = self.classify_model(model)
        enabled = 1 if self.should_enable(context_length, tags, free_tokens) else 0
        now = time.time()

        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.execute("""INSERT OR REPLACE INTO models VALUES (?,?,?,?,?,?,?,?,?)""",
                (provider, model, context_length, free_tokens,
                 ",".join(tags), 50.0, enabled,
                 now, now))
            conn.commit()

    def get_enabled_models(self, task: str = None) -> list:
        """Возвращает список включённых моделей, опционально фильтруя по задаче."""
        with sqlite3.connect(str(DB_PATH)) as conn:
            if task:
                rows = conn.execute(
                    "SELECT provider, model, context_length, tags FROM models WHERE enabled=1 AND tags LIKE ?",
                    (f"%{task}%",)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT provider, model, context_length, tags FROM models WHERE enabled=1"
                ).fetchall()
            return [{"provider": r[0], "model": r[1], "context_length": r[2], "tags": r[3]} for r in rows]

    def get_stats(self):
        """Статистика реестра."""
        with sqlite3.connect(str(DB_PATH)) as conn:
            total = conn.execute("SELECT COUNT(*) FROM models").fetchone()[0]
            enabled = conn.execute("SELECT COUNT(*) FROM models WHERE enabled=1").fetchone()[0]
            return {"total": total, "enabled": enabled}

registry = ModelRegistry()
