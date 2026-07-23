from .base import BaseProvider
class GitHubProvider(BaseProvider):
    name = "github"
    base_url = "https://models.github.ai/inference"
    env_prefix = "GITHUB_TOKEN"
    models = ["gpt-4o-mini"]  # только эта модель работает на GitHub Models
