from .base import BaseProvider
class GitHubProvider(BaseProvider):
    name = "github"
    base_url = "https://models.inference.ai.azure.com"
    env_prefix = "GITHUB_TOKEN"
    models = ["gpt-4o-mini", "gpt-4o"]
