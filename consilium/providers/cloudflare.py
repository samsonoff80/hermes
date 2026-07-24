from .base import BaseProvider
class CloudflareProvider(BaseProvider):
    name = "cloudflare"
    base_url = "https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run"
    env_prefix = "CLOUDFLARE_API_KEY"
    has_api = False
    models = ["@cf/openai/gpt-oss-120b", "@cf/meta/llama-3.2-3b-instruct"]
    format = "cloudflare"
