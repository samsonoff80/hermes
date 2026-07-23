from .base import BaseProvider
class GitHubProvider(BaseProvider):
    name = "github"
    base_url = "https://models.github.ai/inference"
    env_prefix = "GITHUB_TOKEN"
    models = ["azureml://registries/azureml-meta/models/Meta-Llama-3.1-405B-Instruct/versions/1", "azureml://registries/azureml-meta/models/Meta-Llama-3.1-8B-Instruct/versions/1", "azureml://registries/azure-openai/models/gpt-4o/versions/2"]
