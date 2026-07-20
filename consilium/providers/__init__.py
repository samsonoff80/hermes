"""Consilium Providers — модульная архитектура FreeLLMAPI-style.
Каждый провайдер в отдельном файле. Вкл/выкл через enabled.
Триал-ключи исключены. Только вечно-бесплатные."""
import logging
logger = logging.getLogger("consilium.providers")

from .openrouter import OpenRouterProvider
from .groq import GroqProvider
from .mistral import MistralProvider
from .github import GitHubProvider
from .sambanova import SambaNovaProvider
from .hf import HFProvider
from .cloudflare import CloudflareProvider
from .siliconflow import SiliconFlowProvider
from .reka import RekaProvider
from .aihorde import AIHordeProvider
from .deepinfra import DeepInfraProvider
from .together import TogetherProvider

ALL_PROVIDERS = [
    OpenRouterProvider(),
    GroqProvider(),
    MistralProvider(),
    GitHubProvider(),
    SambaNovaProvider(),
    HFProvider(),
    CloudflareProvider(),
                    SiliconFlowProvider(),
    RekaProvider(),
                AIHordeProvider(),
    DeepInfraProvider(),
    TogetherProvider(),
]

PROVIDERS = [p.to_dict() for p in ALL_PROVIDERS if p.enabled]
ENABLED_COUNT = len(PROVIDERS)
TOTAL_COUNT = len(ALL_PROVIDERS)

logger.info(f"Consilium Providers: {ENABLED_COUNT}/{TOTAL_COUNT} enabled")

__all__ = ['PROVIDERS', 'ALL_PROVIDERS']
