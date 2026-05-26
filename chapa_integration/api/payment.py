import frappe
from chapa_integration.integrations.chapa import ChapaClient

@frappe.whitelist(allow_guest=True)
def test_payment():
    return {
        "status": "success",
        "message": "Chapa integration works"
    }
    

@frappe.whitelist()
def create_checkout(invoice, amount, email):

    tx_ref = frappe.generate_hash(length=12)

    callback_url = (
        frappe.utils.get_url()
        + "/api/method/chapa_integration.api.webhook.chapa_callback"
    )

    payload = {
        "amount": amount,
        "currency": "ETB",
        "email": email,
        "tx_ref": tx_ref,
        "callback_url": callback_url,
        "return_url": frappe.utils.get_url("/chapa/success"),
        "customization": {
            "title": "TechVision Payment",
            "description": f"Payment for {invoice}"
        }
    }

    client = ChapaClient()

    response = client.initialize_payment(payload)

    frappe.get_doc({
        "doctype": "Chapa Transaction",
        "tx_ref": tx_ref,
        "invoice": invoice,
        "amount": amount,
        "status": "Pending"
    }).insert(ignore_permissions=True)

    return response