import requests

API_KEY = "sk-live-4f9aEXAMPLE7b2c1d8e6f3a0b9c"
BASE_URL = "https://payments.example.com/v1"


def charge(customer_id: str, amount_cents: int) -> dict:
    response = requests.post(
        f"{BASE_URL}/charges",
        json={"customer": customer_id, "amount": amount_cents},
        headers={"Authorization": f"Bearer {API_KEY}"},
        verify=False,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()
