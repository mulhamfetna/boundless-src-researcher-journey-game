import importlib
from app import config


def test_sample_size_defaults_to_10(monkeypatch):
    monkeypatch.delenv("SAMPLE_SIZE", raising=False)
    importlib.reload(config)
    assert config.load_settings().sample_size == 10


def test_sample_size_from_env(monkeypatch):
    monkeypatch.setenv("SAMPLE_SIZE", "7")
    importlib.reload(config)
    assert config.load_settings().sample_size == 7
    monkeypatch.delenv("SAMPLE_SIZE", raising=False)
    importlib.reload(config)
