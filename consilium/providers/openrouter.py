from .base import BaseProvider

class OpenRouterProvider(BaseProvider):
    name = "openrouter"
    base_url = "https://openrouter.ai/api/v1"
    env_prefix = "OPENROUTER_API_KEY"
    models = ["nvidia/nemotron-3-ultra-550b-a55b:free", "nvidia/nemotron-3-super-120b-a12b:free", "tencent/hy3:free", "poolside/laguna-xs-2.1:free", "poolside/laguna-m.1:free", "google/gemma-4-26b-a4b-it:free", "google/gemma-4-31b-it:free", "cohere/north-mini-code:free", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free", "nvidia/nemotron-3-nano-30b-a3b:free", "openai/gpt-oss-20b:free", "nvidia/nemotron-nano-9b-v2:free"]
    
    def get_headers(self, key):
        return {
            'Authorization': f'Bearer {key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://consilium.ai',
            'X-Title': 'Consilium',
        }
