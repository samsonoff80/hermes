from .base import BaseProvider
class SambaNovaProvider(BaseProvider):
    name = "sambanova"
    base_url = "https://api.sambanova.ai/v1"
    env_prefix = "SAMBANOVA_API_KEY"
    models = ["DeepSeek-V3.1", "DeepSeek-V3.2", "Meta-Llama-3.3-70B-Instruct"]
