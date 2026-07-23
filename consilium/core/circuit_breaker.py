#!/usr/bin/env python3
"""Circuit Breaker — временно отключает провайдеры после серии ошибок."""
import time, threading, logging

logger = logging.getLogger("consilium.circuit_breaker")

class CircuitBreaker:
    # README документирует порог 5 сетевых ошибок — код держал 10.
    def __init__(self, threshold=5, cooldown=60):
        self.threshold = threshold
        self.cooldown = cooldown
        self.failures = {}
        self.disabled_until = {}
        self.lock = threading.Lock()
        self.on_open = None  # коллбэк для алертинга

    def record_failure(self, name):
        opened = False
        with self.lock:
            self.failures[name] = self.failures.get(name, 0) + 1
            if self.failures[name] >= self.threshold and name not in self.disabled_until:
                self.disabled_until[name] = time.time() + self.cooldown
                opened = True
        if opened:
            logger.warning(f"🔴 {name}: circuit breaker OPEN ({self.cooldown}s)")
            if self.on_open:
                try:
                    self.on_open(name)
                except Exception as e:
                    logger.warning(f"circuit breaker alert failed: {e}")
    
    def record_success(self, name):
        with self.lock:
            self.failures[name] = 0
            self.disabled_until.pop(name, None)
    
    def is_available(self, name):
        with self.lock:
            if name in self.disabled_until:
                if time.time() < self.disabled_until[name]:
                    return False
                del self.disabled_until[name]
                self.failures[name] = 0
                logger.info(f"🟢 {name}: circuit breaker CLOSED")
            return True

circuit_breaker = CircuitBreaker()
