import frappe
import json


@frappe.whitelist(allow_guest=True)
def chapa_webhook():

    data = frappe.request.get_json()

    frappe.logger().info(data)

    event = data.get("event")

    if event == "charge.success":

        tx_ref = data.get("tx_ref")

        frappe.call(
            "chapa_integration.api.verify_payment",
            trx_ref=tx_ref,
        )

    return "OK"