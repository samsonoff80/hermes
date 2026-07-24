"""Базовый класс провайдера"""
from pathlib import Path
import os

class BaseProvider:
    name: str = ""
    base_url: str = ""
    env_prefix: str = ""
    keyless: bool = False
    has_api: bool = True  # есть ли /models endpoint
    models: list = []
    enabled: bool = False
    keys: list = []
    format: str = "openai"  # openai | cloudflare | aihorde | huggingface
    # Дневные лимиты для стартовой оценки провайдера (0 = неизвестно)
    rpd: int = 0
    tpd: int = 0

    def __init__(self):
        self.load_keys()
        self.enabled = self.keyless or bool(self.keys)

    def load_keys(self):
        """Ключи из .env рядом с модулем ИЛИ из переменных окружения.

        Порядок: сначала os.environ (systemd EnvironmentFile, docker -e),
        затем .env-файл. Это устраняет расхождение с consilium_server.load_keys(),
        который читал только os.getenv после load_dotenv().
        Поддерживается префикс 'enc:' — ключ расшифровывается на лету.
        """
        if self.keyless or not self.env_prefix:
            self.keys = []
            return

        env = {}
        env_file = Path(__file__).parent.parent / '.env'
        if env_file.exists():
            with open(env_file, encoding='utf-8') as fh:
                for line in fh:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        env[k.strip()] = v.strip().strip('"').strip("'")
        # os.environ имеет приоритет над файлом
        env.update({k: v for k, v in os.environ.items() if k.startswith(self.env_prefix)})

        self.keys = []
        i = 1
        misses = 0
        # Допускаем дырки в нумерации (KEY_1, KEY_3) — не обрываемся на первой
        while i <= 64 and misses < 8:
            k = env.get(f'{self.env_prefix}_{i}', '').strip()
            i += 1
            if not k:
                misses += 1
                continue
            misses = 0
            if 'trial' in k.lower():
                continue
            resolved = self._maybe_decrypt(k)
            if resolved:  # нерасшифрованный ключ не кладём — иначе уйдёт пустой Bearer
                self.keys.append(resolved)

    @staticmethod
    def _maybe_decrypt(raw: str) -> str:
        if not raw.startswith('enc:'):
            return raw
        try:
                        return raw[4:]  # encryption disabled
        except Exception:
            import logging
            logging.getLogger('consilium.providers').error(
                'Не удалось расшифровать ключ (enc:) — проверьте CONSILIUM_ENCRYPTION_KEY'
            )
            return ''
    
    def get_headers(self, key):
        return {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
    
    def get_chat_url(self):
        return f'{self.base_url}/chat/completions'
    
    def to_dict(self):
        return {
            'name': self.name,
            'base_url': self.base_url,
            'key_prefix': self.env_prefix,
            'models': self.models,
            # БЫЛО жёстко 'openai' — из-за этого ветки cloudflare/aihorde/huggingface
            # в consilium_server были недостижимы, а не-OpenAI провайдеры вызывались
            # как OpenAI-совместимые и всегда падали.
            'format': self.format,
            'keyless': self.keyless,
            'enabled': self.enabled,
            'keys': self.keys,
            'key_index': 0,
            'cooldown_until': 0.0,
            'rpd': self.rpd,
            'tpd': self.tpd,
        }
