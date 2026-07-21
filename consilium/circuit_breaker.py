#!/usr/bin/env python3
"""Circuit Breaker — временно отключает провайдеры после серии ошибок."""
import time, threading, logging

logger = logging.getLogger("consilium.circuit_breaker")

class CircuitBreaker:
    def __init__(self, threshold=5, cooldown=60):
        self.threshold = threshold
        self.cooldown = cooldown
        self.failures = {}
        self.disabled_until = {}
        self.lock = threading.Lock()
    
    def record_failure(self, name):
        """Записывает ошибку для провайдера."""
        with self.lock:
            self.failures[name] = self.failures.get(name, 0) + 1
            if self.failures[name] >= self.threshold:
                self.disabled_until[name] = time.time() + self.cooldown
                logger.warning(f"🔴 {name}: circuit breaker OPEN ({self.cooldown}s) after {self.threshold} failures")
    
    def record_success(self, name):
        """Сбрасывает счётчик ошибок после успешного запроса."""
        with self.lock:
            self.failures[name] = 0
            self.disabled_until.pop(name, None)
            logger.debug(f"🟢 {name}: circuit breaker reset")
    
    def is_available(self, name):
        """Проверяет доступность провайдера."""
        with self.lock:
            if name in self.disabled_until:
                if time.time() < self.disabled_until[name]:
                    return False
                # Cooldown истёк - сбрасываем
                del self.disabled_until[name]
                self.failures[name] = 0
                logger.info(f"🟢 {name}: circuit breaker CLOSED (cooldown expired)")
            return True

circuit_breaker = CircuitBreaker()
