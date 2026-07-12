from src.cache import should_refresh


def test_no_refresh_by_default(monkeypatch):
    monkeypatch.delenv("REFRESH", raising=False)
    assert should_refresh() is False


def test_refresh_flag(monkeypatch):
    monkeypatch.setenv("REFRESH", "true")
    assert should_refresh() is True
