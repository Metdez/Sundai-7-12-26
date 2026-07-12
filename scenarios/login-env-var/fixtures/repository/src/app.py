"""Login entry point for the demo web app."""
from src.auth import create_token

_USERS = {"alice": "wonderland", "bob": "builder"}


def login(username: str, password: str) -> str:
    if _USERS.get(username) != password:
        raise PermissionError("invalid credentials")
    return create_token(username)
