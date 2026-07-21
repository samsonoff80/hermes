from .base import BaseProvider

class CloudflareProvider(BaseProvider):
    name = "cloudflare"
    base_url = "https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run"
    env_prefix = "CLOUDFLARE_API_KEY"
    has_api = False
    # Только чат-модели (убраны embedding, image, tts модели)
    models = ["@cf/meta/llama-3.2-3b-instruct", "@cf/openai/gpt-oss-120b", "@cf/pipecat-ai/smart-turn-v2"]
    format = "cloudflare"
