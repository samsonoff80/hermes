import random, logging

logger = logging.getLogger("consilium.error")

class ErrorHandler:
    @staticmethod
    def classify(error: Exception) -> str:
        s = getattr(getattr(error, 'response', None), 'status_code', 0)
        m = str(error).lower()
        if s == 429 or 'rate limit' in m: return "rate_limit"
        if s in (401,403) or 'unauthorized' in m: return "auth"
        if 'timeout' in m or 'connect' in m: return "network"
        if s >= 500: return "server"
        return "unknown"
    
    @staticmethod
    def should_retry(error: Exception) -> bool:
        return ErrorHandler.classify(error) in ("rate_limit", "network", "server")
    
    @staticmethod
    def retry_delay(error: Exception, attempt: int) -> float:
        d = min(1.0 * (2 ** attempt), 60.0)
        return d * (0.5 + random.random() * 0.5)
