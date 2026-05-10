import frappe
import requests
import json

from frappe.utils import get_url

from .utils import (
    get_base_url,
    get_headers,
)

@frappe.whitelist(allow_guest=True)
def test_payment():

    return frappe.call(
        "chapa_integration.api.initialize_payment",
        amount=10,
        email="mehariwamlake@gmail.com",
        full_name="mehariw amlake",
        reference_doctype="Test",
        reference_name="TEST-001",
    )
    
@frappe.whitelist(allow_guest=True)
def initialize_payment(
    amount: float,
    email: str,
    full_name: str | None = None,
    phone_number: str | None = None,
    currency: str = "ETB",
    reference_doctype: str | None = None,
    reference_name: str | None = None,
    callback_method: str | None = None,
    metadata: dict | None = None,
):

    tx_ref = frappe.generate_hash(length=20)

    payload = {
        "amount": str(amount),
        "currency": currency,
        "email": email,
        "tx_ref": tx_ref,
        "callback_url": get_url(
            "/api/method/chapa_integration.api.verify_payment"
        ),
        "return_url": get_url("/payment-success"),
    }

    if full_name:
        names = full_name.split(" ", 1)

        payload["first_name"] = names[0]

        if len(names) > 1:
            payload["last_name"] = names[1]

    if phone_number:
        payload["phone_number"] = phone_number

    response = requests.post(
        f"{get_base_url()}/transaction/initialize",
        headers=get_headers(),
        json=payload,
    )

    data = response.json()

    frappe.logger().info(data)

    if data.get("status") != "success":

        error_message = data.get("message")

        if isinstance(error_message, dict):
            error_message = json.dumps(
                error_message,
                indent=2
            )

        frappe.throw(
            error_message or "Chapa initialization failed"
        )

    checkout_url = data["data"]["checkout_url"]

    doc = frappe.get_doc({
        "doctype": "Chapa Transaction",
        "tx_ref": tx_ref,
        "status": "Pending",
        "amount": amount,
        "currency": currency,
        "email": email,
        "phone_number": phone_number,
        "full_name": full_name,
        "reference_doctype": reference_doctype,
        "reference_name": reference_name,
        "callback_method": callback_method,
        "checkout_url": checkout_url,
        "metadata": metadata,
        "raw_response": json.dumps(data, indent=2),
    })

    doc.insert(ignore_permissions=True)

    return {
        "tx_ref": tx_ref,
        "checkout_url": checkout_url,
    }


@frappe.whitelist(allow_guest=True)
def verify_payment():

    tx_ref = frappe.form_dict.get("tx_ref")

    if not tx_ref:
        return "Missing transaction reference"

    transaction_name = frappe.db.get_value(
        "Chapa Transaction",
        {"tx_ref": tx_ref},
    )

    if not transaction_name:
        return "Transaction not found"

    doc = frappe.get_doc(
        "Chapa Transaction",
        transaction_name
    )

    response = requests.get(
        f"{get_base_url()}/transaction/verify/{tx_ref}",
        headers=get_headers(),
    )

    data = response.json()

    frappe.logger().info(data)

    if data.get("status") != "success":

        doc.status = "Failed"
        doc.save(ignore_permissions=True)

        return "Verification failed"

    chapa_data = data.get("data", {})

    payment_status = chapa_data.get("status")

    if payment_status == "success":

        doc.status = "Success"
        doc.chapa_id = chapa_data.get("id")
        doc.raw_response = json.dumps(data, indent=2)

        doc.save(ignore_permissions=True)

        run_callback(doc)

        return "Payment Successful"

    doc.status = "Failed"
    doc.save(ignore_permissions=True)

    return "Payment Failed"


def run_callback(transaction_doc):

    if not transaction_doc.callback_method:
        return

    try:

        method = frappe.get_attr(
            transaction_doc.callback_method
        )

        method(transaction_doc)

    except Exception:

        frappe.log_error(
            frappe.get_traceback(),
            "Chapa Callback Error"
        )