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


@frappe.whitelist()
def register_user_domain(meeting_id):
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication is required"), frappe.AuthenticationError)
	if not meeting_id:
		frappe.throw(_("Meeting ID is required"), frappe.ValidationError)

	user = frappe.session.user
	user_info = frappe.db.get_value("User", user, ["email", "full_name"], as_dict=True) or {}
	user_email = user_info.get("email")
	if not user_email:
		frappe.throw(_("The current NextGRP user has no email address"), frappe.ValidationError)
	return meet_backend_service.register_user_domain(
		meeting_id,
		user_email,
		user_info.get("full_name") or user,
	)


@frappe.whitelist()
def record_user_domain(meeting_id, user_email, host_name, user_name=None):
	"""Store a NextGRP user's entry into a meeting on this Meet instance."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication is required"), frappe.AuthenticationError)
	request = getattr(frappe.local, "request", None)
	authorization = request.headers.get("Authorization", "") if request else ""
	if not authorization.lower().startswith("token "):
		frappe.throw(_("Server API authentication is required"), frappe.AuthenticationError)
	if not meeting_id or not user_email or not host_name:
		frappe.throw(_("Meeting, user email and host name are required"), frappe.ValidationError)

	if not frappe.db.exists("Sae Meeting", meeting_id):
		frappe.throw(_("Meeting not found"), frappe.DoesNotExistError)

	entry = frappe.get_doc(
		{
			"doctype": "User Domain",
			"meeting": meeting_id,
			"user_email": user_email.strip().lower(),
			"user_name": (user_name or "").strip(),
			"host_name": host_name.strip().lower().rstrip("."),
			"joined_at": frappe.utils.now_datetime(),
		}
	).insert(ignore_permissions=True)
	return entry.name
