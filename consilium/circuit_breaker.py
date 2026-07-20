#!/usr/bin/env python3
"""Circuit Breaker — временно отключает провайдеры после серии ошибок."""
import time, threading, logging

logger = logging.getLogger("consilium.circuit_breaker")

class CircuitBreaker:
    def __init__(self, threshold=10, cooldown=60):
        self.threshold = threshold
        self.cooldown = cooldown
        self.failures = {}
        self.disabled_until = {}
        self.lock = threading.Lock()
    
    def record_failure(self, name):
        with self.lock:
            self.failures[name] = self.failures.get(name, 0) + 1
            if self.failures[name] >= self.threshold:
                self.disabled_until[name] = time.time() + self.cooldown
                logger.warning(f"🔴 {name}: circuit breaker OPEN ({self.cooldown}s)")
    
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
