import frappe
import requests

class ChapaClient:
    def __init__(self):
        settings = frappe.get_single("Chapa Settings")

        self.secret_key = settings.get_password("secret_key")
        self.base_url = (
            "https://api.chapa.co/v1"
        )

    def initialize_payment(self, data):
        url = f"{self.base_url}/transaction/initialize"

        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }

        response = requests.post(
            url,
            json=data,
            headers=headers
        )

        return response.json()

    def verify_payment(self, tx_ref):
        url = f"{self.base_url}/transaction/verify/{tx_ref}"

        headers = {
            "Authorization": f"Bearer {self.secret_key}"
        }

        response = requests.get(url, headers=headers)

        return response.json()