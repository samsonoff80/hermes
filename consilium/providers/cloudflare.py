from .base import BaseProvider
class CloudflareProvider(BaseProvider):
    name = "cloudflare"
    base_url = "https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run"
    env_prefix = "CLOUDFLARE_API_KEY"
    has_api = False
    models = ["@cf/pipecat-ai/smart-turn-v2", "@cf/openai/gpt-oss-120b", "@cf/baai/bge-m3", "@cf/huggingface/distilbert-sst-2-int8", "@cf/google/gemma-2b-it-lora", "@cf/black-forest-labs/flux-2-klein-9b", "@cf/meta/llama-3.2-3b-instruct", "@cf/meta/llama-guard-3-8b", "@cf/qwen/qwen3-embedding-0.6b", "@cf/myshell-ai/melotts"]
    format = "cloudflare"
