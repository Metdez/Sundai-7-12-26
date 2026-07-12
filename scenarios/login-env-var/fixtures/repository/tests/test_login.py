from src.app import login


def test_login_returns_token():
    token = login("alice", "wonderland")
    assert token.startswith("token-")
