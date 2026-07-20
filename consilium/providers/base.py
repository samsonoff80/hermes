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
    
    def __init__(self):
        self.load_keys()
        self.enabled = self.keyless or bool(self.keys)
    
    def load_keys(self):
        if self.keyless or not self.env_prefix:
            self.keys = []
            return
        env_file = Path(__file__).parent.parent / '.env'
        if not env_file.exists():
            self.keys = []
            return
        env = {}
        for line in open(env_file):
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
        
        self.keys = []
        i = 1
        while True:
            k = env.get(f'{self.env_prefix}_{i}', '').strip()
            if not k:
                break
            if 'trial' not in k.lower():
                self.keys.append(k)
            i += 1
    
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
            'format': 'openai',
            'keyless': self.keyless,
            'enabled': self.enabled,
            'keys': self.keys,
            'key_index': 0,
            'cooldown_until': 0.0,
        }
