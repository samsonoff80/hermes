#!/usr/bin/env python3
"""Provider Statistics + Dynamic Provider Score (DPS).

Заменяет жёсткий PRIORITY динамическим рейтингом.

Состояние живёт В ПАМЯТИ и сбрасывается в SQLite батчами: на VIM4 открывать
соединение на каждый запрос (как было раньше) — это лишние сотни мс и
блокировки при конкурентных запросах. При старте состояние восстанавливается
из БД, поэтому баллы переживают перезапуск.

Формула (0..100), считается на пару provider/model:

    DPS = 40*success + 25*latency + 20*limits + 15*health

    success  — байесовски сглаженная доля успехов:
               (ok + 2) / (ok + fail + 4)
               Сглаживание не даёт новичку с 1/1 обойти проверенного с 900/1000
               и не даёт одному сбою обнулить провайдера.
    latency  — exp(-avg_latency / 2.0): 0.5с ≈ 0.78, 2с ≈ 0.37, 5с ≈ 0.08
    limits   — log10(rpd)/4 — дневной лимит провайдера (1000 RPD ≈ 0.75)
    health   — свежесть сбоев: штраф за 429/5xx/timeout затухает за ~10 минут

Жёсткие гейты (cooldown, disabled, circuit breaker) применяются ОТДЕЛЬНО
в fallback_manager: провайдер с активным cooldown не выбирается независимо
от баллов.
"""
import sqlite3
import time
import threading
import math
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Optional

logger = logging.getLogger("consilium.stats")

DB_PATH = Path(__file__).parent / "provider_stats.db"

# Веса компонентов
W_SUCCESS = 40.0
W_LATENCY = 25.0
W_LIMITS = 20.0
W_HEALTH = 15.0

LATENCY_TAU = 2.0        # секунды, постоянная затухания
HEALTH_DECAY = 600.0     # за сколько секунд «забывается» сбой
FLUSH_INTERVAL = 30.0    # как часто сбрасывать в SQLite
EMA_ALPHA = 0.3          # вес свежего замера латентности


class ProviderStats:
    def __init__(self):
        self.lock = threading.Lock()
        self._cache: Dict[str, dict] = {}
        self._dirty = False
        self._last_flush = time.time()
        self._init_db()
        self._load_state()

    # ---------- persistence ----------

    def _init_db(self):
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""CREATE TABLE IF NOT EXISTS stats (
                key TEXT PRIMARY KEY,
                provider TEXT,
                model TEXT,
                success INTEGER DEFAULT 0,
                fail INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                avg_latency REAL DEFAULT 0,
                last_used REAL DEFAULT 0,
                last_fail REAL DEFAULT 0,
                fail_kind TEXT DEFAULT '')""")
            conn.commit()

    def _load_state(self):
        """Восстановление баллов после перезапуска."""
        try:
            with sqlite3.connect(str(DB_PATH)) as conn:
                rows = conn.execute(
                    "SELECT key, provider, model, success, fail, total_tokens, "
                    "avg_latency, last_used, last_fail, fail_kind FROM stats"
                ).fetchall()
            for r in rows:
                self._cache[r[0]] = {
                    "provider": r[1], "model": r[2], "success": r[3], "fail": r[4],
                    "total_tokens": r[5], "avg_latency": r[6], "last_used": r[7],
                    "last_fail": r[8], "fail_kind": r[9],
                }
            if rows:
                logger.info(f"📊 Восстановлено записей статистики: {len(rows)}")
        except Exception as e:
            logger.warning(f"📊 Не удалось загрузить статистику: {e}")

    def flush(self, force: bool = False):
        """Батчевый сброс в SQLite."""
        with self.lock:
            if not self._dirty:
                return
            if not force and (time.time() - self._last_flush) < FLUSH_INTERVAL:
                return
            snapshot = list(self._cache.items())
            self._dirty = False
            self._last_flush = time.time()
        try:
            with sqlite3.connect(str(DB_PATH)) as conn:
                conn.executemany(
                    "INSERT OR REPLACE INTO stats (key, provider, model, success, fail, "
                    "total_tokens, avg_latency, last_used, last_fail, fail_kind) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?)",
                    [(k, v["provider"], v["model"], v["success"], v["fail"],
                      v["total_tokens"], v["avg_latency"], v["last_used"],
                      v["last_fail"], v["fail_kind"]) for k, v in snapshot]
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"📊 Сброс статистики не удался: {e}")

    # ---------- запись ----------

    @staticmethod
    def _key(provider: str, model: str = "") -> str:
        return f"{provider}|{model}" if model else provider

    def _entry(self, provider: str, model: str) -> dict:
        key = self._key(provider, model)
        e = self._cache.get(key)
        if e is None:
            e = {"provider": provider, "model": model, "success": 0, "fail": 0,
                 "total_tokens": 0, "avg_latency": 0.0, "last_used": 0.0,
                 "last_fail": 0.0, "fail_kind": ""}
            self._cache[key] = e
        return e

    def record_success(self, provider: str, latency: float, tokens: int = 0, model: str = ""):
        with self.lock:
            e = self._entry(provider, model)
            e["success"] += 1
            e["total_tokens"] += int(tokens or 0)
            # EMA вместо среднего: свежая латентность важнее исторической
            e["avg_latency"] = (latency if e["avg_latency"] <= 0
                                else EMA_ALPHA * latency + (1 - EMA_ALPHA) * e["avg_latency"])
            e["last_used"] = time.time()
            self._dirty = True
        self.flush()

    def record_failure(self, provider: str, kind: str = "error", model: str = ""):
        """kind: 429 | 5xx | timeout | network | error"""
        with self.lock:
            e = self._entry(provider, model)
            e["fail"] += 1
            e["last_fail"] = time.time()
            e["fail_kind"] = kind
            self._dirty = True
        self.flush()

    # ---------- расчёт баллов ----------

    def get_dynamic_score(self, provider: str, model: str = "", rpd: int = 0) -> float:
        """DPS в диапазоне 0..100. Чем выше — тем раньше провайдер в цепочке."""
        with self.lock:
            e = self._cache.get(self._key(provider, model))
            if e is None and model:
                # нет статистики по модели — берём агрегат по провайдеру
                e = self._aggregate_unlocked(provider)
            if e is None:
                e = {"success": 0, "fail": 0, "avg_latency": 0.0,
                     "last_fail": 0.0, "fail_kind": ""}
            success, fail = e["success"], e["fail"]
            avg_latency, last_fail = e["avg_latency"], e["last_fail"]
            fail_kind = e["fail_kind"]

        # 1. Успешность с байесовским сглаживанием
        s_success = (success + 2) / (success + fail + 4)

        # 2. Латентность (нет замеров -> оптимистичная середина)
        s_latency = math.exp(-avg_latency / LATENCY_TAU) if avg_latency > 0 else 0.5

        # 3. Дневной лимит
        s_limits = min(1.0, math.log10(rpd) / 4.0) if rpd > 0 else 0.3

        # 4. Здоровье: свежий сбой бьёт сильно, старый — почти нет
        if last_fail <= 0:
            s_health = 1.0
        else:
            age = time.time() - last_fail
            severity = {"429": 1.0, "5xx": 0.8, "timeout": 0.8,
                        "network": 0.9}.get(fail_kind, 0.5)
            s_health = 1.0 - severity * math.exp(-age / HEALTH_DECAY)

        return (W_SUCCESS * s_success + W_LATENCY * s_latency
                + W_LIMITS * s_limits + W_HEALTH * s_health)

    def _aggregate_unlocked(self, provider: str) -> Optional[dict]:
        """Сводка по всем моделям провайдера. Вызывать под self.lock."""
        rows = [v for v in self._cache.values() if v["provider"] == provider]
        if not rows:
            return None
        lat = [r["avg_latency"] for r in rows if r["avg_latency"] > 0]
        return {
            "success": sum(r["success"] for r in rows),
            "fail": sum(r["fail"] for r in rows),
            "avg_latency": (sum(lat) / len(lat)) if lat else 0.0,
            "last_fail": max(r["last_fail"] for r in rows),
            "fail_kind": max(rows, key=lambda r: r["last_fail"])["fail_kind"],
        }

    def get_priority(self) -> List[Tuple[str, float, float]]:
        """(provider, success_rate, avg_latency) — для дашборда."""
        with self.lock:
            agg: Dict[str, dict] = {}
            for v in self._cache.values():
                a = agg.setdefault(v["provider"], {"s": 0, "f": 0, "lat": []})
                a["s"] += v["success"]
                a["f"] += v["fail"]
                if v["avg_latency"] > 0:
                    a["lat"].append(v["avg_latency"])
        out = []
        for name, a in agg.items():
            rate = a["s"] / (a["s"] + a["f"] + 1)
            lat = sum(a["lat"]) / len(a["lat"]) if a["lat"] else 0.0
            out.append((name, rate, lat))
        out.sort(key=lambda x: (-x[1], x[2]))
        return out

    def get_ranked_providers(self, providers_list: list) -> List[Tuple[str, float]]:
        scored = [(p.get("name", ""),
                   self.get_dynamic_score(p.get("name", ""), rpd=p.get("rpd", 0)))
                  for p in providers_list if p.get("name")]
        scored.sort(key=lambda x: -x[1])
        return scored

    def snapshot(self) -> List[dict]:
        """Полный срез для /stats/providers."""
        with self.lock:
            items = list(self._cache.values())
        out = []
        for v in items:
            total = v["success"] + v["fail"]
            out.append({
                "provider": v["provider"],
                "model": v["model"],
                "success": v["success"],
                "fail": v["fail"],
                "success_rate": round(v["success"] / total, 4) if total else None,
                "avg_latency": round(v["avg_latency"], 3),
                "total_tokens": v["total_tokens"],
                "last_fail_kind": v["fail_kind"] or None,
                "dps": round(self.get_dynamic_score(v["provider"], v["model"]), 2),
            })
        out.sort(key=lambda x: -x["dps"])
        return out


provider_stats = ProviderStats()
