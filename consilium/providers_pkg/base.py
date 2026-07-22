from abc import ABC, abstractmethod
from dataclasses import dataclass
import httpx, logging

logger = logging.getLogger("consilium")

@dataclass
class ProviderConfig:
    name: str; platform: str; base_url: str; api_key: str = ""
    timeout: int = 15000; rpm: int = 60; tpm: int = 100000

class BaseProvider(ABC):
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.client = None
    
    @abstractmethod
    async def chat_completion(self, messages, model, **kwargs) -> dict:
        pass
    
    @abstractmethod
    async def stream_completion(self, messages, model, **kwargs):
        pass
    
    @abstractmethod
    async def list_models(self) -> list:
        pass
    
    async def close(self):
        if self.client:
            await self.client.aclose()
