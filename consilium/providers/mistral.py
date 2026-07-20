from .base import BaseProvider

class MistralProvider(BaseProvider):
    name = "mistral"
    base_url = "https://api.mistral.ai/v1"
    env_prefix = "MISTRAL_API_KEY"
    models = ["codestral-2508", "codestral-latest", "mistral-small-2603", "mistral-small-latest", "magistral-small-latest"]
