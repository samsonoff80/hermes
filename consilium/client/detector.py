import re, logging

logger = logging.getLogger("consilium.client")

class ClientDetector:
    @staticmethod
    def detect(user_agent: str) -> str:
        if not user_agent: return "unknown"
        m = re.search(r'hermes-cli/(\d+\.\d+)', user_agent)
        return m.group(1) if m else "unknown"
