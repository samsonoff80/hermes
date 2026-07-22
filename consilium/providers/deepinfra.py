from .base import BaseProvider
class DeepInfraProvider(BaseProvider):
    name = "deepinfra"
    base_url = "https://api.deepinfra.com/v1/openai"
    env_prefix = "DEEPINFRA_API_KEY"
    models = ["Qwen/Qwen3-VL-30B-A3B-Instruct", "Qwen/Qwen3-Next-80B-A3B-Instruct", "mistralai/Mistral-Small-24B-Instruct-2501", "Qwen/Qwen3.5-397B-A17B", "NousResearch/Hermes-3-Llama-3.1-405B"]
