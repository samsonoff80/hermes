#!/usr/bin/env python3
"""Rate Limiter — per-key лимиты с сохранением состояния в SQLite.

Что было сломано:
- _load_state() имел пустое тело цикла: состояние из БД НЕ восстанавливалось,
  хотя README обещал persistence.
- is_available() открывал соединение с SQLite на каждый вызов и возвращал
  кортеж (bool, reason) — в булевом контексте непустой кортеж всегда истинен,
  поэтому проверка «if rate_limiter.is_available(...)» была бы бесполезной.
- Эскалация cooldown не работала: COOLDOWN_STEPS[0] использовался всегда.
- mark_429 затирал счётчик подряд идущих 429 единицей.

Теперь состояние живёт в памяти, в SQLite сбрасывается лениво.
"""
import time
import sqlite3
import threading
import logging
from pathlib import Path
from typing import Tuple, Optional, Dict

logger = logging.getLogger("consilium.rate_limiter")

DB_PATH = Path(__file__).parent / "rate_limits.db"
COOLDOWN_STEPS = [90, 300, 900, 3600, 21600]


class RateLimiter:
    def __init__(self):
        self.lock = threading.Lock()
        self._state: Dict[Tuple[str, int], dict] = {}
        self._dirty = False
        self._last_flush = 0.0
        self._init_db()
        self._load_state()

    def _init_db(self):
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""CREATE TABLE IF NOT EXISTS rate_limits (
                provider TEXT, key_index INTEGER,
                rpd_count INTEGER DEFAULT 0, tpd_count INTEGER DEFAULT 0,
                day_start REAL DEFAULT 0, cooldown_until REAL DEFAULT 0,
                consecutive_429 INTEGER DEFAULT 0, disabled INTEGER DEFAULT 0,
                PRIMARY KEY (provider, key_index))""")
            conn.commit()

    def _load_state(self):
        """Раньше тело цикла было пустым — состояние терялось при рестарте."""
        try:
            with sqlite3.connect(str(DB_PATH)) as conn:
                rows = conn.execute(
                    "SELECT provider, key_index, rpd_count, tpd_count, day_start, "
                    "cooldown_until, consecutive_429, disabled FROM rate_limits"
                ).fetchall()
            for r in rows:
                self._state[(r[0], r[1])] = {
                    "rpd": r[2], "tpd": r[3], "day_start": r[4],
                    "cooldown_until": r[5], "consecutive_429": r[6], "disabled": bool(r[7]),
                }
            if rows:
                active = sum(1 for v in self._state.values()
                             if v["disabled"] or v["cooldown_until"] > time.time())
                logger.info(f"⏳ Восстановлено ключей: {len(rows)} (под ограничением: {active})")
        except Exception as e:
            logger.warning(f"⏳ Не удалось загрузить состояние лимитов: {e}")

    def _entry(self, provider: str, key_index: int) -> dict:
        e = self._state.get((provider, key_index))
        if e is None:
            e = {"rpd": 0, "tpd": 0, "day_start": time.time(),
                 "cooldown_until": 0.0, "consecutive_429": 0, "disabled": False}
            self._state[(provider, key_index)] = e
        return e

    def flush(self, force: bool = False):
        with self.lock:
            if not self._dirty:
                return
            if not force and (time.time() - self._last_flush) < 15.0:
                return
            snapshot = list(self._state.items())
            self._dirty = False
            self._last_flush = time.time()
        try:
            with sqlite3.connect(str(DB_PATH)) as conn:
                conn.executemany(
                    "INSERT OR REPLACE INTO rate_limits (provider, key_index, rpd_count, "
                    "tpd_count, day_start, cooldown_until, consecutive_429, disabled) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    [(p, ki, v["rpd"], v["tpd"], v["day_start"], v["cooldown_until"],
                      v["consecutive_429"], int(v["disabled"]))
                     for (p, ki), v in snapshot]
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"⏳ Сброс лимитов не удался: {e}")

    def is_available(self, provider: str, key_index: int = 0) -> Tuple[bool, Optional[str]]:
        """(доступен, причина_отказа). Читает только память."""
        with self.lock:
            e = self._state.get((provider, key_index))
            if e is None:
                return True, None
            if e["disabled"]:
                return False, "disabled"
            if e["cooldown_until"] > time.time():
                return False, f"cooldown:{int(e['cooldown_until'] - time.time())}s"
        return True, None

    def any_key_available(self, provider: str, key_count: int) -> bool:
        """Есть ли хоть один рабочий ключ у провайдера."""
        if key_count <= 0:
            return self.is_available(provider, 0)[0]
        return any(self.is_available(provider, i)[0] for i in range(key_count))

    def record_request(self, provider: str, key_index: int = 0, tokens: int = 0):
        with self.lock:
            e = self._entry(provider, key_index)
            now = time.time()
            if now - e["day_start"] > 86400:
                e["rpd"] = 0
                e["tpd"] = 0
                e["day_start"] = now
            e["rpd"] += 1
            e["tpd"] += int(tokens or 0)
            self._dirty = True
        self.flush()

    def mark_429(self, provider: str, key_index: int = 0):
        """Эскалация cooldown: 90с → 5м → 15м → 1ч → 6ч."""
        with self.lock:
            e = self._entry(provider, key_index)
            e["consecutive_429"] = min(e["consecutive_429"] + 1, len(COOLDOWN_STEPS))
            step = COOLDOWN_STEPS[e["consecutive_429"] - 1]
            e["cooldown_until"] = time.time() + step
            self._dirty = True
        logger.warning(f"⏳ {provider}:{key_index} 429 → cooldown {step}s")
        self.flush()

    def mark_402(self, provider: str, key_index: int = 0):
        with self.lock:
            e = self._entry(provider, key_index)
            e["disabled"] = True
            self._dirty = True
        logger.warning(f"❌ {provider}:{key_index} 401/402/403 → ключ отключён")
        self.flush(force=True)

    def mark_success(self, provider: str, key_index: int = 0):
        with self.lock:
            e = self._state.get((provider, key_index))
            if e is None:
                return
            if e["consecutive_429"] or e["cooldown_until"]:
                e["consecutive_429"] = 0
                e["cooldown_until"] = 0.0
                self._dirty = True
        self.flush()

    def reset(self, provider: str, key_index: int = 0):
        """Ручной сброс (для отладки и админ-эндпоинтов)."""
        with self.lock:
            self._state.pop((provider, key_index), None)
            self._dirty = True
        self.flush(force=True)


rate_limiter = RateLimiter()
