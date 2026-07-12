"""Payment gateway client."""
import requests

GATEWAY = "https://payments.internal/api/charge"


def charge(order_id: str, amount_cents: int) -> dict:
    response = requests.post(GATEWAY, json={"order": order_id, "amount": amount_cents})
    response.raise_for_status()
    return response.json()
