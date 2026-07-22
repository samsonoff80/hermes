from .base import ProviderConfig
from .openai_compat import OpenAICompatProvider
from proxy.manager import proxy_manager
import os, logging
from dotenv import load_dotenv
from pathlib import Path

logger = logging.getLogger("consilium")

class ProviderRegistry:
    def __init__(self):
        self._instances = {}
        self._configs = {}
        self._key_indexes = {}
        # Загружаем .env с ключами
        load_dotenv(Path.home() / ".hermes" / "skills" / "consilium" / ".env")
    
    def setup(self, providers_config: list):
        for p in providers_config:
            cfg = ProviderConfig(**p)
            instance = OpenAICompatProvider(cfg)
            instance.client = proxy_manager.get_client(cfg.platform, cfg.base_url, cfg.timeout)
            self._instances[cfg.name] = instance
            self._configs[cfg.name] = cfg
            self._key_indexes[cfg.name] = 0
            keys = self._get_keys(cfg.name)
            logger.info(f"Provider: {cfg.name} ({len(keys)} keys)")
    
    def get(self, name: str):
        if name not in self._instances:
            return None
        instance = self._instances[name]
        keys = self._get_keys(name)
        if keys:
            idx = self._key_indexes[name] % len(keys)
            self._key_indexes[name] = idx + 1
            instance.config.api_key = keys[idx]
        return instance
    
    def _get_keys(self, name: str) -> list:
        prefix_map = {
            "openrouter": "OPENROUTER_API_KEY",
            "sambanova": "SAMBANOVA_API_KEY",
            "groq": "GROQ_API_KEY",
            "github": "GITHUB_TOKEN",
            "mistral": "MISTRAL_API_KEY",
            "cloudflare": "CLOUDFLARE_API_KEY",
            "cerebras": "CEREBRAS_API_KEY",
            "deepinfra": "DEEPINFRA_API_KEY",
        }
        prefix = prefix_map.get(name, name.upper() + "_API_KEY")
        keys = []
        for s in ["_1", "_2", "_3"]:
            k = os.getenv(prefix + s, "")
            if k: keys.append(k)
        return keys
    
    def all_names(self) -> list:
        return list(self._instances.keys())
    
    async def close_all(self):
        for i in self._instances.values():
            await i.close()

registry = ProviderRegistry()
