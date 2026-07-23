from .base import BaseProvider
class TogetherProvider(BaseProvider):
    name = "together"
    base_url = "https://api.together.xyz/v1"
    env_prefix = "TOGETHER_API_KEY"
    models = ["meta-llama/Llama-3.3-70B-Instruct"]
