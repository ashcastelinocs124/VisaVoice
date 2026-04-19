import os
from visavoice.config import Settings

def test_settings_reads_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("BACKEND_BASE_URL", "http://x:1")
    monkeypatch.setenv("CALLER_HASH_SALT", "salt")
    s = Settings()
    assert s.openai_api_key == "sk-test"
    assert s.backend_base_url == "http://x:1"
    assert s.caller_hash_salt == "salt"

def test_settings_defaults(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("CALLER_HASH_SALT", "salt")
    monkeypatch.delenv("BACKEND_BASE_URL", raising=False)
    s = Settings()
    assert s.backend_base_url == "http://localhost:8080"
