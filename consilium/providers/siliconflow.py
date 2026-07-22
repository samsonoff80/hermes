from .base import BaseProvider
class SiliconFlowProvider(BaseProvider):
    name = "siliconflow"
    base_url = "https://api.siliconflow.cn/v1"
    env_prefix = "SILICONFLOW_API_KEY"
    models = ["Qwen/Qwen2.5-7B-Instruct"]
