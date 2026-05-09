import frappe
from .config import SANDBOX_URL, PRODUCTION_URL


def get_settings():
    return frappe.get_single("Chapa Settings")


def get_base_url():

    settings = get_settings()

    if settings.sandbox_mode:
        return SANDBOX_URL

    return PRODUCTION_URL


def get_headers():

    settings = get_settings()

    return {
        "Authorization": f"Bearer {settings.get_password('secret_key')}",
        "Content-Type": "application/json",
    }