#!/usr/bin/env python3
"""
Rate Limiter — объединённый (наш + FreeLLMAPI).
- Динамические лимиты из заголовков x-ratelimit-*
- Cooldown escalation: 90s → 5m → 15m → 1h → 6h
- 402/403 → ключ выключается
- 429 → cooldown + следующий ключ
- Дефолтные лимиты если заголовков нет
- Thread-safe
"""
import time, threading, logging, json
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger('consilium.rate_limiter')

COOLDOWN_STEPS = [90, 300, 900, 3600, 21600]

# Дефолтные лимиты (перезаписываются из заголовков)
DEFAULT_LIMITS = {
    'openrouter':    {'rpm': 20,  'tpm': 200000, 'rpd': 200,  'tpd': 2000000},
    'groq':          {'rpm': 30,  'tpm': 6000,   'rpd': 1000, 'tpd': 100000},
    'mistral':       {'rpm': 300, 'tpm': 1000000,'rpd': 10000,'tpd': 10000000},
    'github':        {'rpm': 10,  'tpm': 50000,  'rpd': 50,   'tpd': 500000},
    'sambanova':     {'rpm': 20,  'tpm': 100000, 'rpd': 500,  'tpd': 1000000},
    'hf':            {'rpm': 10,  'tpm': 50000,  'rpd': 100,  'tpd': 500000},
    'cloudflare':    {'rpm': 2,   'tpm': 10000,  'rpd': 100,  'tpd': 500000},
    'deepinfra':     {'rpm': 10,  'tpm': 50000,  'rpd': 100,  'tpd': 500000},
    'pollinations':  {'rpm': 1,   'tpm': 5000,   'rpd': 10,   'tpd': 50000},
    'ovh':           {'rpm': 2,   'tpm': 5000,   'rpd': 20,   'tpd': 50000},
    'kilo':          {'rpm': 5,   'tpm': 10000,  'rpd': 50,   'tpd': 100000},
    'bazaarlink':    {'rpm': 5,   'tpm': 10000,  'rpd': 50,   'tpd': 100000},
}
FALLBACK_LIMITS = {'rpm': 5, 'tpm': 10000, 'rpd': 50, 'tpd': 100000}

@dataclass
class KeyStats:
    rpm_count: int = 0
    tpm_count: int = 0
    rpd_count: int = 0
    tpd_count: int = 0
    window_start: float = field(default_factory=lambda: time.time())
    day_start: float = field(default_factory=lambda: time.time())
    cooldown_until: float = 0.0
    consecutive_429: int = 0
    disabled: bool = False

class RateLimiter:
    def __init__(self):
        self.stats: dict[str, KeyStats] = {}
        self.dynamic_limits: dict[str, dict] = {}  # из заголовков
        self.lock = threading.RLock()
        self._load_state()
    
    def _key_id(self, provider: str, key_index: int) -> str:
        return f"{provider}:{key_index}"
    
    def get_limits(self, provider: str) -> dict:
        """Лимиты: dynamic > default > fallback"""
        return self.dynamic_limits.get(provider) or DEFAULT_LIMITS.get(provider) or FALLBACK_LIMITS
    
    def update_from_headers(self, provider: str, headers: dict):
        """FreeLLMAPI-style: парсим x-ratelimit-* заголовки"""
        limits = {}
        mapping = {
            'x-ratelimit-limit-requests': 'rpm',
            'x-ratelimit-limit-tokens': 'tpm',
            'x-ratelimit-remaining-requests': None,
            'x-ratelimit-remaining-tokens': None,
        }
        for header, key in mapping.items():
            val = headers.get(header, '')
            if val and val.isdigit() and key:
                limits[key] = int(val)
        if limits and any(limits.values()):
            self.dynamic_limits[provider] = limits
            logger.debug(f"📊 {provider} limits: {limits}")
    
    def is_available(self, provider: str, key_index: int = 0) -> Tuple[bool, Optional[str]]:
        kid = self._key_id(provider, key_index)
        limits = self.get_limits(provider)
        now = time.time()
        
        with self.lock:
            s = self.stats.setdefault(kid, KeyStats())
            
            if s.disabled:
                return False, "disabled"
            if now < s.cooldown_until:
                return False, f"cooldown:{int(s.cooldown_until - now)}s"
            
            if now - s.window_start > 60:
                s.rpm_count = s.tpm_count = 0
                s.window_start = now
            if now - s.day_start > 86400:
                s.rpd_count = s.tpd_count = 0
                s.day_start = now
            
            for metric, count in [('rpm', s.rpm_count), ('tpm', s.tpm_count), ('rpd', s.rpd_count), ('tpd', s.tpd_count)]:
                if count >= limits.get(metric, 999999):
                    return False, f"{metric}:{count}/{limits[metric]}"
            
            return True, None
    
    def record_request(self, provider: str, key_index: int, tokens: int):
        with self.lock:
            s = self.stats.setdefault(self._key_id(provider, key_index), KeyStats())
            s.rpm_count += 1
            s.tpm_count += tokens
            s.rpd_count += 1
            s.tpd_count += tokens
    
    def mark_429(self, provider: str, key_index: int):
        with self.lock:
            s = self.stats.setdefault(self._key_id(provider, key_index), KeyStats())
            s.consecutive_429 += 1
            step = min(max(s.consecutive_429 - 1, 0), len(COOLDOWN_STEPS) - 1)
            s.cooldown_until = time.time() + COOLDOWN_STEPS[step]
            logger.warning(f"⏳ {provider}:{key_index} 429 → cooldown {COOLDOWN_STEPS[step]}s")
    
    def mark_402(self, provider: str, key_index: int):
        with self.lock:
            self.stats.setdefault(self._key_id(provider, key_index), KeyStats()).disabled = True
            logger.warning(f"❌ {provider}:{key_index} 402 → disabled")
    
    def mark_success(self, provider: str, key_index: int):
        with self.lock:
            s = self.stats.setdefault(self._key_id(provider, key_index), KeyStats())
            s.consecutive_429 = 0  # сброс при успехе
    
    def _save_state(self):
        state = {k: {'disabled': v.disabled, 'cooldown_until': v.cooldown_until} for k, v in self.stats.items()}
        state_file = Path(__file__).parent / 'provider_state.json'
        with open(state_file, 'w') as f:
            json.dump(state, f)
    
    def _load_state(self):
        state_file = Path(__file__).parent / 'provider_state.json'
        if state_file.exists():
            try:
                with open(state_file) as f:
                    state = json.load(f)
                for k, v in state.items():
                    s = KeyStats()
                    s.disabled = v.get('disabled', False)
                    s.cooldown_until = v.get('cooldown_until', 0)
                    self.stats[k] = s
            except:
                pass

rate_limiter = RateLimiter()
