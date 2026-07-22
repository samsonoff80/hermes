#!/usr/bin/env python3
"""
Fallback Manager — реестр провайдеров и построение цепочек отказоустойчивости.

Отличия от прежней версии:
- Порядок в цепочке задаёт не жёсткий список PRIORITY, а динамический балл (DPS)
  из provider_stats. PRIORITY остался только как слабый тай-брейкер для
  холодного старта, когда статистики ещё нет.
- get_chain() больше не возвращает пустой список: раньше chains["code"] мог быть
  пустым (например, нет ни одной модели с тегом code), и .get(task, default)
  возвращал именно пустой список — дефолт не срабатывал, потому что ключ
  существовал. Итог: target_provider=None -> HTTP 503 на ровном месте.
- Появился resolve_model(): запрос с явным именем модели раньше вообще не
  находил провайдера (роутинг работал только для model="auto").
- Учитываются жёсткие гейты: cooldown/disabled ключей и circuit breaker.
"""
import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger("consilium.fallback")

# Слабый тай-брейкер для холодного старта (нет статистики).
COLD_START_PRIORITY = ["mistral", "groq", "sambanova", "deepinfra", "hf",
                       "cloudflare", "openrouter", "github", "together",
                       "siliconflow", "reka", "aihorde"]

TAG_RULES = {
    "chat": ["llama", "mistral", "gpt", "gemma", "qwen", "hermes", "nemotron"],
    "code": ["coder", "deepseek", "code", "hy3", "codestral"],
    "search": ["gemini", "scout", "sonnet", "gpt", "perplexity"],
    "analysis": ["large", "ultra", "r1", "reasoning", "think"],
}


class FallbackManager:
    def __init__(self):
        self.cache_file = Path(__file__).parent / "fallback_chain.json"
        self.chains: Dict[str, List[dict]] = {}
        self.all_entries: List[dict] = []
        self.last_update = 0.0
        self.ttl = 3600

    def build_chains(self, providers_data: list):
        """Строит цепочки из всех провайдеров, у которых есть ключи (или keyless)."""
        chains: Dict[str, List[dict]] = {"chat": [], "code": [], "search": [], "analysis": []}
        all_entries: List[dict] = []

        for p in providers_data:
            name = p.get("name", "")
            keys = p.get("keys", [])
            keyless = p.get("keyless", False)
            if not keys and not keyless:
                continue

            try:
                cold = COLD_START_PRIORITY.index(name)
            except ValueError:
                cold = 99

            for model in p.get("models", []):
                tags = [tag for tag, kws in TAG_RULES.items()
                        if any(kw in model.lower() for kw in kws)]
                if not tags:
                    tags = ["chat"]

                entry = {
                    "provider": name,
                    "model": model,
                    "keys": len(keys),
                    "keyless": keyless,
                    "tags": tags,
                    "cold_priority": cold,
                    "rpd": p.get("rpd", 0),
                    "format": p.get("format", "openai"),
                }
                all_entries.append(entry)
                for tag in tags:
                    chains[tag].append(entry)

        self.chains = chains
        self.all_entries = all_entries
        self.last_update = time.time()
        self._save()

        for tag, chain in chains.items():
            providers = {e["provider"] for e in chain}
            logger.info(f"📋 {tag}: {len(chain)} моделей от {len(providers)} провайдеров")
        if not all_entries:
            logger.error("❌ Ни одного доступного провайдера: проверьте .env и ключи")

    # ---------- выбор ----------

    def _rank(self, entries: List[dict], gate=None) -> List[dict]:
        """Сортирует по убыванию DPS. gate(provider) -> bool отсеивает недоступных."""
        from provider_stats import provider_stats

        alive, blocked = [], []
        for e in entries:
            if gate is not None and not gate(e["provider"]):
                blocked.append(e)
                continue
            alive.append(e)

        def score(e):
            return provider_stats.get_dynamic_score(e["provider"], e["model"], e.get("rpd", 0))

        alive.sort(key=lambda e: (-score(e), e["cold_priority"], -e["keys"]))
        # Заблокированные не выбрасываем совсем — они уходят в самый хвост цепочки
        # как последний шанс, если живых не осталось.
        blocked.sort(key=lambda e: (e["cold_priority"], -e["keys"]))
        return alive + blocked

    def get_chain(self, task: str, gate=None) -> List[dict]:
        """Цепочка для задачи, отсортированная по баллам. Никогда не пустая,
        если в системе есть хотя бы один рабочий провайдер."""
        entries = self.chains.get(task) or []
        if not entries:
            # Ключ существует, но список пуст -> честно падаем на chat, затем на всё
            entries = self.chains.get("chat") or self.all_entries
            if entries:
                logger.warning(f"⚠️ Цепочка '{task}' пуста — использую запасную ({len(entries)})")
        return self._rank(entries, gate)

    def resolve_model(self, model_name: str, gate=None) -> List[dict]:
        """Цепочка для явно запрошенной модели.

        Сначала точное совпадение имени, затем подстрочное (Hermes может прислать
        'groq/llama-3.3-70b' или просто 'llama-3.3-70b'). Пустой список означает,
        что вызывающий код должен откатиться на обычный роутинг.
        """
        if not model_name or model_name == "auto":
            return []
        needle = model_name.strip()
        short = needle.split("/", 1)[1] if "/" in needle else needle

        exact = [e for e in self.all_entries if e["model"] == needle or e["model"] == short]
        if exact:
            return self._rank(exact, gate)
        loose = [e for e in self.all_entries
                 if short.lower() in e["model"].lower() or e["model"].lower() in short.lower()]
        return self._rank(loose, gate)

    # ---------- кэш ----------

    def _save(self):
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump({"updated": time.strftime("%Y-%m-%dT%H:%M:%S"),
                           "chains": self.chains}, f, indent=2, ensure_ascii=False)
        except OSError as e:
            logger.warning(f"Не удалось сохранить кэш цепочек: {e}")

    def load(self) -> bool:
        if not self.cache_file.exists():
            return False
        try:
            with open(self.cache_file, encoding="utf-8") as f:
                data = json.load(f)
            self.chains = data.get("chains", {})
            self.all_entries = [e for chain in self.chains.values() for e in chain]
            return True
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Не удалось загрузить кэш цепочек: {e}")
            return False


fallback = FallbackManager()
