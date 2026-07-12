"""Token creation for the demo web app."""
import hashlib
import os


def create_token(username: str) -> str:
    secret = os.environ.get("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET is not configured")
    payload = f"{username}:{secret}".encode("utf-8")
    return "token-" + hashlib.sha256(payload).hexdigest()[:24]
