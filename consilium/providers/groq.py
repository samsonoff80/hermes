from .base import BaseProvider

class GroqProvider(BaseProvider):
    name = "groq"
    base_url = "https://api.groq.com/openai/v1"
    env_prefix = "GROQ_API_KEY"
    models = ["llama-3.1-8b-instant", "llama-3.3-70b-versatile"]
