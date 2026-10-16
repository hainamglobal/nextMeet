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
	if method_name == "meet.api.meeting.create":
		user = frappe.db.get_value("User", frappe.session.user, ["full_name", "email"], as_dict=True) or {}
		parsed_params = {
			**parsed_params,
			"created_by_name": user.get("full_name") or frappe.session.user,
			"created_by_email": user.get("email") or "",
		}
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


def record_meeting_participant(meeting, user_name, user_email=None):
	"""Record an admitted participant without using a Meet account email."""
	from frappe.utils import now_datetime

	name = (user_name or "").strip()[:140]
	if not name:
		return
	entry = frappe.get_doc(
		{
			"doctype": "User Domain",
			"meeting": meeting.name,
			"user_email": (user_email or "").strip().lower(),
			"user_name": name,
			"host_name": (meeting.host_name or frappe.local.site).strip().lower().rstrip("."),
			"joined_at": now_datetime(),
		}
	)
	entry.insert(ignore_permissions=True)


def record_meeting_guest(meeting, guest_name):
	"""Record guest entry; any email remains sourced only from MTP's authenticated call."""
	from frappe.utils import now_datetime

	name = (guest_name or "").strip()[:140]
	if not name:
		return
	previous = frappe.get_all(
		"User Domain",
		filters={
			"meeting": meeting.name,
			"host_name": (meeting.host_name or frappe.local.site).strip().lower().rstrip("."),
			"user_name": name,
		},
		fields=["name", "user_email", "joined_at"],
		order_by="joined_at desc",
		limit=1,
	)
	if previous and (now_datetime() - previous[0].joined_at).total_seconds() < 120:
		frappe.db.set_value("User Domain", previous[0].name, "joined_at", now_datetime(), update_modified=False)
		return previous[0].name
	entry = frappe.get_doc(
		{
			"doctype": "User Domain",
			"meeting": meeting.name,
			"user_email": "",
			"user_name": name,
			"host_name": (meeting.host_name or frappe.local.site).strip().lower().rstrip("."),
			"joined_at": now_datetime(),
		}
	)
	entry.insert(ignore_permissions=True)


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
