from src.settings import load_settings


def test_boot():
    settings = load_settings()
    assert settings["debug"] is True
