from .base import BaseProvider
class RekaProvider(BaseProvider):
    name = "reka"
    base_url = "https://api.reka.ai/v1"
    env_prefix = "REKA_API_KEY"
    models = ["reka-core"]
