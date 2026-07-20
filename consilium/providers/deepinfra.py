from .base import BaseProvider
class DeepInfraProvider(BaseProvider):
    name = "deepinfra"
    base_url = "https://api.deepinfra.com/v1/openai"
    env_prefix = "DEEPINFRA_API_KEY"
    models = ["Qwen/Qwen3-30B-A3B", "Qwen/Qwen3.6-27B", "Qwen/Qwen3-32B", "mistralai/Mistral-Small-3.2-24B-Instruct-2506", "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"]
