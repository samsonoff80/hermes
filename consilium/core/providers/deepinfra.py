from .base import BaseProvider
class DeepInfraProvider(BaseProvider):
    name = "deepinfra"
    base_url = "https://api.deepinfra.com/v1/openai"
    env_prefix = "DEEPINFRA_API_KEY"
    models = ["Qwen/Qwen3-ASR-0.6B", "Qwen/Qwen3-14B", "Qwen/Qwen3.5-9B", "Qwen/Qwen3-235B-A22B-Thinking-2507", "Qwen/Qwen3-TTS-VoiceDesign"]
