#!/usr/bin/env python3
"""
Fallback Manager — умный реестр провайдеров.
- Автообнаружение всех провайдеров из providers/*.py
- Ключей может быть 1, 3, 5, 10 — система считает все
- Теги моделей: chat, code, search, analysis
- Кэширует цепочки в fallback_chain.json
- Обновляется при старте и раз в час
"""
import json, time, logging
from pathlib import Path

logger = logging.getLogger("consilium.fallback")

class FallbackManager:
    def __init__(self):
        self.cache_file = Path(__file__).parent / "fallback_chain.json"
        self.chains = {}
        self.last_update = 0
        self.ttl = 3600  # 1 час
    
    def build_chains(self, providers_data: list):
        """Строит цепочки из ВСЕХ провайдеров с ключами."""
        chains = {"chat": [], "code": [], "search": [], "analysis": []}
        
        # Приоритет провайдеров по лимитам
        PRIORITY = ["mistral", "groq", "sambanova", "deepinfra", "hf", 
                     "cloudflare", "openrouter", "github"]
        
        # Теги моделей по ключевым словам
        TAG_RULES = {
            "chat": ["llama", "mistral", "gpt", "gemma", "qwen", "hermes"],
            "code": ["coder", "deepseek", "code", "hy3"],
            "search": ["gemini", "scout", "sonnet", "gpt"],
            "analysis": ["large", "ultra", "r1"],
        }
        
        all_entries = []
        
        for p in providers_data:
            name = p.get("name", "")
            keys = p.get("keys", [])
            keyless = p.get("keyless", False)
            
            # Пропускаем если нет ключей и не keyless
            if not keys and not keyless:
                continue
            
            # Приоритет провайдера (0 =最高)
            try:
                priority = PRIORITY.index(name)
            except ValueError:
                priority = 99
            
            for model in p.get("models", []):
                # Определяем теги модели
                tags = []
                for tag, keywords in TAG_RULES.items():
                    if any(kw in model.lower() for kw in keywords):
                        tags.append(tag)
                
                # Если теги не определены — модель универсальная
                if not tags:
                    tags = ["chat"]
                
                all_entries.append({
                    "provider": name,
                    "model": model,
                    "keys": len(keys),
                    "keyless": keyless,
                    "tags": tags,
                    "priority": priority,
                })
        
        # Сортируем: сначала по приоритету провайдера, потом по количеству ключей
        all_entries.sort(key=lambda x: (x["priority"], -x["keys"]))
        
        # Распределяем по цепочкам
        for entry in all_entries:
            for tag in entry["tags"]:
                if entry not in chains[tag]:
                    chains[tag].append(entry)
        
        self.chains = chains
        self.last_update = time.time()
        self._save()
        
        for tag, chain in chains.items():
            providers = set(e["provider"] for e in chain)
            logger.info(f"📋 {tag}: {len(chain)} моделей от {len(providers)} провайдеров")
    
    def get_chain(self, task: str) -> list:
        """Возвращает цепочку для задачи."""
        if time.time() - self.last_update > self.ttl:
            logger.info("⏰ Кэш устарел — нужен refresh")
        
        return self.chains.get(task, self.chains.get("chat", []))
    
    def _save(self):
        """Сохраняет кэш в JSON."""
        data = {
            "updated": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "chains": self.chains,
        }
        with open(self.cache_file, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load(self):
        """Загружает кэш из JSON."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file) as f:
                    data = json.load(f)
                    self.chains = data.get("chains", {})
                    return True
            except:
                pass
        return False

fallback = FallbackManager()
