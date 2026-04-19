import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    caller_hash_salt: str
    backend_base_url: str = "http://localhost:8080"
    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""

    def __init__(self):
        object.__setattr__(self, "openai_api_key", _required("OPENAI_API_KEY"))
        object.__setattr__(self, "caller_hash_salt", _required("CALLER_HASH_SALT"))
        object.__setattr__(self, "backend_base_url",
                           os.environ.get("BACKEND_BASE_URL", "http://localhost:8080"))
        object.__setattr__(self, "livekit_url",       os.environ.get("LIVEKIT_URL", ""))
        object.__setattr__(self, "livekit_api_key",   os.environ.get("LIVEKIT_API_KEY", ""))
        object.__setattr__(self, "livekit_api_secret", os.environ.get("LIVEKIT_API_SECRET", ""))


def _required(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        raise RuntimeError(f"Missing required env var: {name}")
    return v
