#!/usr/bin/env python3
"""Балльная система провайдеров — динамический приоритет на основе статистики."""
import sqlite3, time, logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger("consilium.scoring")

DB_PATH = Path(__file__).parent / "provider_scores.db"

# Веса для формулы расчёта баллов
WEIGHTS = {
    "w1": 1.0,   # success_rate
    "w2": 0.5,   # latency (1 / (1 + avg_latency))
    "w3": 0.3,   # normalized_rpd
    "k1": 0.4,   # penalty for 429
    "k2": 0.4,   # penalty for 5xx
    "k3": 0.3,   # penalty for timeouts
    "k4": 0.2,   # penalty for small context
}

MIN_CONTEXT = 8000  # минимальный контекст для штрафа
WINDOW_SECONDS = 300  # окно для "recent" ошибок (5 минут)

class ProviderScoring:
    """Система динамического скоринга провайдеров."""
    
    def __init__(self):
        self._init_db()
        self._load_config()
    
    def _init_db(self):
        """Инициализирует базу данных SQLite."""
        with sqlite3.connect(str(DB_PATH)) as conn:
            # Таблица статистики провайдеров
            conn.execute("""CREATE TABLE IF NOT EXISTS provider_stats (
                provider TEXT PRIMARY KEY,
                total_requests INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                timeout_count INTEGER DEFAULT 0,
                rate_limit_count INTEGER DEFAULT 0,
                server_error_count INTEGER DEFAULT 0,
                total_prompt_tokens INTEGER DEFAULT 0,
                total_completion_tokens INTEGER DEFAULT 0,
                total_latency_seconds REAL DEFAULT 0,
                context_window INTEGER DEFAULT 0,
                max_rpd INTEGER DEFAULT 0,
                last_request_time REAL DEFAULT 0,
                last_success_time REAL DEFAULT 0,
                last_failure_time REAL DEFAULT 0
            )""")
            
            # Таблица истории ошибок (для скользящего окна)
            conn.execute("""CREATE TABLE IF NOT EXISTS error_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT,
                error_type TEXT,  -- '429', '5xx', 'timeout', 'other'
                timestamp REAL
            )""")
            
            # Индексы для быстрого доступа
            conn.execute("CREATE INDEX IF NOT EXISTS idx_provider_stats ON provider_stats(provider)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_error_provider ON error_history(provider)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_error_timestamp ON error_history(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_error_type ON error_history(error_type)")
            
            conn.commit()
    
    def _load_config(self):
        """Загружает конфигурацию из файла (опционально)."""
        config_file = Path(__file__).parent / "scoring_config.json"
        if config_file.exists():
            try:
                import json
                with open(config_file) as f:
                    config = json.load(f)
                    WEIGHTS.update(config.get("weights", {}))
                logger.info(f"⚙️ Загружены веса из {config_file}")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось загрузить конфиг: {e}")
    
    def _cleanup_old_errors(self, provider: str, window: float = WINDOW_SECONDS):
        """Удаляет старые записи ошибок за пределами окна."""
        cutoff = time.time() - window
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.execute("DELETE FROM error_history WHERE provider=? AND timestamp < ?", 
                        (provider, cutoff))
            conn.commit()
    
    def _get_recent_errors(self, provider: str, error_type: str, window: float = WINDOW_SECONDS) -> int:
        """Возвращает количество ошибок за скользящее окно."""
        cutoff = time.time() - window
        with sqlite3.connect(str(DB_PATH)) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM error_history WHERE provider=? AND error_type=? AND timestamp > ?",
                (provider, error_type, cutoff)
            ).fetchone()[0]
        return count
    
    def record_success(self, provider: str, latency: float, prompt_tokens: int = 0, 
                      completion_tokens: int = 0, context_window: int = 0):
        """Записывает успешный запрос."""
        with sqlite3.connect(str(DB_PATH)) as conn:
            # Обновляем статистику
            conn.execute("""INSERT INTO provider_stats (provider) 
                VALUES (?) ON CONFLICT(provider) DO NOTHING""", (provider,))
            
            conn.execute("""UPDATE provider_stats SET
                total_requests = total_requests + 1,
                success_count = success_count + 1,
                total_prompt_tokens = total_prompt_tokens + ?,
                total_completion_tokens = total_completion_tokens + ?,
                total_latency_seconds = total_latency_seconds + ?,
                context_window = MAX(context_window, ?),
                last_request_time = ?,
                last_success_time = ?
                WHERE provider = ?""",
                (prompt_tokens, completion_tokens, latency, context_window, 
                 time.time(), time.time(), provider))
            conn.commit()
        
        logger.debug(f"✅ {provider}: success recorded (latency: {latency:.2f}s)")
    
    def record_failure(self, provider: str, error_type: str = "other"):
        """Записывает ошибку."""
        with sqlite3.connect(str(DB_PATH)) as conn:
            # Обновляем статистику
            conn.execute("""INSERT INTO provider_stats (provider) 
                VALUES (?) ON CONFLICT(provider) DO NOTHING""", (provider,))
            
            if error_type == "429":
                conn.execute("UPDATE provider_stats SET rate_limit_count = rate_limit_count + 1 WHERE provider = ?", 
                            (provider,))
            elif error_type == "5xx":
                conn.execute("UPDATE provider_stats SET server_error_count = server_error_count + 1 WHERE provider = ?", 
                            (provider,))
            elif error_type == "timeout":
                conn.execute("UPDATE provider_stats SET timeout_count = timeout_count + 1 WHERE provider = ?", 
                            (provider,))
            else:
                conn.execute("UPDATE provider_stats SET failure_count = failure_count + 1 WHERE provider = ?", 
                            (provider,))
            
            conn.execute("""UPDATE provider_stats SET 
                total_requests = total_requests + 1,
                last_request_time = ?,
                last_failure_time = ?
                WHERE provider = ?""",
                (time.time(), time.time(), provider))
            
            # Записываем в историю ошибок
            conn.execute("INSERT INTO error_history (provider, error_type, timestamp) VALUES (?, ?, ?)",
                        (provider, error_type, time.time()))
            
            conn.commit()
        
        # Очищаем старые ошибки
        self._cleanup_old_errors(provider)
        
        logger.debug(f"❌ {provider}: {error_type} recorded")
    
    def get_score(self, provider: str, context_window: int = 128000, max_rpd: int = 1000) -> float:
        """Вычисляет балл для провайдера.
        
        Формула:
        score = w1 * success_rate 
               + w2 * (1 / (1 + avg_latency)) 
               + w3 * (rpd / max_rpd) 
               - k1 * recent_429 
               - k2 * recent_5xx 
               - k3 * recent_timeouts 
               - k4 * (1 if context < MIN_CONTEXT else 0)
        
        Args:
            provider: имя провайдера
            context_window: контекстное окно модели
            max_rpd: максимальный дневной лимит (для нормировки)
        
        Returns:
            float: балл провайдера (выше = лучше)
        """
        with sqlite3.connect(str(DB_PATH)) as conn:
            row = conn.execute(
                """SELECT total_requests, success_count, total_latency_seconds, 
                        total_prompt_tokens, total_completion_tokens, context_window, max_rpd 
                 FROM provider_stats WHERE provider = ?""",
                (provider,)
            ).fetchone()
        
        if not row:
            # Новый провайдер - нейтральный балл
            return 0.5
        
        total_requests, success_count, total_latency, total_prompt, total_completion, db_context, db_max_rpd = row
        
        # Вычисляем метрики
        if total_requests == 0:
            success_rate = 0.5  # нейтрально
        else:
            success_rate = success_count / total_requests
        
        if success_count == 0:
            avg_latency = 1.0  # нейтрально
        else:
            avg_latency = total_latency / success_count
        
        # Нормированный RPD
        if max_rpd > 0 and db_max_rpd > 0:
            normalized_rpd = min(db_max_rpd / max_rpd, 1.0)
        else:
            normalized_rpd = 0.5
        
        # Штрафы за недавние ошибки (скользящее окно)
        recent_429 = self._get_recent_errors(provider, "429")
        recent_5xx = self._get_recent_errors(provider, "5xx")
        recent_timeouts = self._get_recent_errors(provider, "timeout")
        
        # Штраф за маленький контекст
        context_penalty = 1 if (context_window < MIN_CONTEXT or db_context < MIN_CONTEXT) else 0
        
        # Вычисляем балл
        w = WEIGHTS
        score = (w["w1"] * success_rate 
                 + w["w2"] * (1 / (1 + avg_latency)) 
                 + w["w3"] * normalized_rpd
                 - w["k1"] * recent_429
                 - w["k2"] * recent_5xx
                 - w["k3"] * recent_timeouts
                 - w["k4"] * context_penalty)
        
        # Ограничиваем диапазон
        score = max(0.0, min(score, 10.0))
        
        return score
    
    def get_all_scores(self) -> Dict[str, float]:
        """Возвращает баллы для всех провайдеров."""
        scores = {}
        with sqlite3.connect(str(DB_PATH)) as conn:
            providers = conn.execute("SELECT DISTINCT provider FROM provider_stats").fetchall()
        
        for (provider,) in providers:
            scores[provider] = self.get_score(provider)
        
        return scores
    
    def get_sorted_providers(self, providers: list[str]) -> list[str]:
        """Возвращает отсортированный список провайдеров по баллам (выше = лучше)."""
        scores = {p: self.get_score(p) for p in providers}
        return sorted(providers, key=lambda p: scores.get(p, 0.5), reverse=True)
    
    def reset_provider(self, provider: str):
        """Сбрасывает статистику для провайдера."""
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.execute("DELETE FROM provider_stats WHERE provider = ?", (provider,))
            conn.execute("DELETE FROM error_history WHERE provider = ?", (provider,))
            conn.commit()
        logger.info(f"🔄 {provider}: статистика сброшена")
    
    def get_stats(self, provider: str) -> Optional[dict]:
        """Возвращает статистику для провайдера."""
        with sqlite3.connect(str(DB_PATH)) as conn:
            row = conn.execute(
                "SELECT * FROM provider_stats WHERE provider = ?",
                (provider,)
            ).fetchone()
        
        if not row:
            return None
        
        columns = ["provider", "total_requests", "success_count", "failure_count", 
                   "timeout_count", "rate_limit_count", "server_error_count",
                   "total_prompt_tokens", "total_completion_tokens", "total_latency_seconds",
                   "context_window", "max_rpd", "last_request_time", "last_success_time", "last_failure_time"]
        
        return dict(zip(columns, row))

# Глобальный экземпляр
provider_scoring = ProviderScoring()
