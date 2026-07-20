from .base import BaseProvider
class AIHordeProvider(BaseProvider):
    name = "aihorde"
    base_url = "https://aihorde.net/api/v1"
    env_prefix = ""
    keyless = True
    has_api = False
    models = ["stable-tsoul-4.2b"]
    format = "aihorde"
