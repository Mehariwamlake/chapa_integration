import frappe
from chapa_integration.integrations.chapa import ChapaClient

@frappe.whitelist(allow_guest=True)
def chapa_callback():

    data = frappe.request.get_json()

    tx_ref = data.get("tx_ref")

    client = ChapaClient()

    verification = client.verify_payment(tx_ref)

    if verification["status"] != "success":
        frappe.throw("Payment verification failed")

    payment_data = verification["data"]

    if payment_data["status"] != "success":
        frappe.throw("Payment not completed")

    transaction = frappe.get_doc(
        "Chapa Transaction",
        {"tx_ref": tx_ref}
    )

    transaction.status = "Paid"
    transaction.save(ignore_permissions=True)

    create_payment_entry(transaction)

    frappe.db.commit()

    return {"message": "Payment verified"}
    
def create_payment_entry(transaction):

    payment_entry = frappe.get_doc({
        "doctype": "Payment Entry",
        "payment_type": "Receive",
        "party_type": "Customer",
        "party": "Guest Customer",
        "paid_amount": transaction.amount,
        "received_amount": transaction.amount,
        "reference_no": transaction.tx_ref,
        "reference_date": frappe.utils.nowdate()
    })

    payment_entry.insert(ignore_permissions=True)
    payment_entry.submit()