from .base import BaseProvider
class HFProvider(BaseProvider):
    name = "hf"
    base_url = "https://router.huggingface.co/v1"
    env_prefix = "HF_TOKEN"
    models = ["google/gemma-4-31B-it", "Qwen/Qwen3.6-35B-A3B", "Qwen/Qwen3.6-27B", "google/gemma-4-26B-A4B-it", "meta-llama/Llama-3.1-8B-Instruct"]
