from .base import BaseProvider
class DeepInfraProvider(BaseProvider):
    name = "deepinfra"
    base_url = "https://api.deepinfra.com/v1/openai"
    env_prefix = "DEEPINFRA_API_KEY"
    models = ["Qwen/Qwen3-14B", "Qwen/Qwen3.5-122B-A10B", "meta-llama/Llama-3.3-70B-Instruct-Turbo", "Qwen/Qwen3.6-27B", "mistralai/Mistral-Nemo-Instruct-2407"]
