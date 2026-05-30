# Copyright (c) 2026, TechVision and contributors
# License: MIT

from urllib.parse import urlencode

import frappe
from frappe import _
from frappe.integrations.utils import create_request_log, make_post_request
from frappe.model.document import Document
from frappe.utils import get_url

from payments.utils import create_payment_gateway


class ChapaSettings(Document):
	supported_currencies = (
		"ETB",
		"USD",
	)

	def on_update(self):
		create_payment_gateway(
			"Chapa",
			settings="Chapa Settings",
			controller="chapa",
		)

		if not self.flags.ignore_mandatory:
			self.validate_chapa_credentials()

	def validate_chapa_credentials(self):
		if self.secret_key:
			headers = {
				"Authorization": f"Bearer {self.get_password(fieldname='secret_key')}"
			}

			try:
				make_post_request(
					"https://api.chapa.co/v1/transaction/initialize",
					headers=headers,
					data={
						"amount": "1",
						"currency": "ETB",
						"email": "test@example.com",
						"first_name": "Test",
						"last_name": "User",
						"tx_ref": "test-ref",
						"callback_url": get_url(),
						"return_url": get_url(),
					},
				)
			except Exception:
				frappe.throw(_("Invalid Chapa Secret Key"))

	def validate_transaction_currency(self, currency):
		if currency not in self.supported_currencies:
			frappe.throw(
				_(
					"Chapa does not support transactions in currency '{0}'"
				).format(currency)
			)

	def get_payment_url(self, **kwargs):
		return get_url(f"./chapa_checkout?{urlencode(kwargs)}")

	def create_request(self, data):
		self.data = frappe._dict(data)

		try:
			self.integration_request = create_request_log(
				self.data,
				service_name="Chapa",
			)

			return self.create_checkout_session()

		except Exception:
			frappe.log_error(frappe.get_traceback(), "Chapa Payment Error")

			return {
				"redirect_to": frappe.redirect_to_message(
					_("Server Error"),
					_("Unable to initialize Chapa payment."),
				),
				"status": 401,
			}

	def create_checkout_session(self):
		headers = {
			"Authorization": f"Bearer {self.get_password(fieldname='secret_key')}"
		}

		payload = {
			"amount": str(self.data.amount),
			"currency": self.data.currency or "ETB",
			"email": self.data.payer_email,
			"first_name": self.data.get("payer_name", "Customer"),
			"last_name": ".",
			"tx_ref": self.integration_request.name,
			"callback_url": get_url(
				f"/api/method/chapa_integration.api.chapa_callback"
			),
			"return_url": get_url(
				f"/payment-success?doctype={self.data.reference_doctype}&docname={self.data.reference_docname}"
			),
			"customization[title]": self.data.description or "Payment",
			"customization[description]": self.data.description or "Payment",
		}

		try:
			response = make_post_request(
				"https://api.chapa.co/v1/transaction/initialize",
				headers=headers,
				data=payload,
			)

			if response.get("status") == "success":
				checkout_url = response["data"]["checkout_url"]

				self.integration_request.db_set(
					"status",
					"Completed",
					update_modified=False,
				)

				return {
					"redirect_to": checkout_url,
					"status": "Completed",
				}

			frappe.log_error(str(response), "Chapa Initialization Failed")

		except Exception:
			frappe.log_error(frappe.get_traceback(), "Chapa Checkout Error")

		return {
			"redirect_to": "payment-failed",
			"status": "Failed",
		}


	def get_gateway_controller(doctype, docname, payment_gateway=None):
		if not payment_gateway:
			reference_doc = frappe.get_doc(doctype, docname)
			payment_gateway = reference_doc.payment_gateway

		return frappe.db.get_value(
			"Payment Gateway",
			payment_gateway,
			"gateway_controller",
		)

	def on_update(self):
		create_payment_gateway(
			"Chapa",
			settings="Chapa Settings",
			controller="chapa"
		)