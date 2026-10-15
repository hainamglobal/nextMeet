"""Authenticated API exposed to MTP for remote Meet operations."""

import frappe
from frappe import _

from meet.services import meet_backend_service


@frappe.whitelist()
def request(method_name, params=None):
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication is required"), frappe.AuthenticationError)
	if not isinstance(method_name, str):
		frappe.throw(_("Meet method is invalid"), frappe.ValidationError)

	parsed_params = frappe.parse_json(params) if isinstance(params, str) else (params or {})
	if not isinstance(parsed_params, dict):
		frappe.throw(_("Meet parameters must be an object"), frappe.ValidationError)
	return meet_backend_service.request(method_name, parsed_params)


@frappe.whitelist()
def health():
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication is required"), frappe.AuthenticationError)
	return meet_backend_service.health()
