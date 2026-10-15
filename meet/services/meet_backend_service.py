"""Application service for MTP's remote Meet operations."""

import frappe
from frappe import _

from meet.client.meet_backend_client import MeetBackendClient, MeetBackendError
from meet.config.backend import get_backend_settings


ALLOWED_METHODS = {
	"frappe.client.get_list",
	"frappe.client.get",
	"run_doc_method",
	"meet.api.meeting.create",
	"meet.api.meeting.get_sfu_connection_details",
	"meet.api.meeting.join_meeting",
	"meet.api.meeting.join_meeting_as_guest",
	"meet.api.meeting.get_waiting_room",
	"meet.api.meeting.approve_join_request",
	"meet.api.meeting.approve_all_join_requests",
	"meet.api.meeting.reject_join_request",
	"meet.api.meeting.promote_to_cohost",
	"meet.api.meeting.check_meeting_access",
}


def request(method_name, params):
	if method_name not in ALLOWED_METHODS:
		frappe.throw(_("Meet method is not allowed"), frappe.PermissionError)

	if method_name in {"frappe.client.get_list", "frappe.client.get", "run_doc_method"}:
		doctype = params.get("doctype") or params.get("dt")
		if doctype != "Sae Meeting":
			frappe.throw(_("Only Sae Meeting documents can be accessed"), frappe.PermissionError)
	if method_name == "run_doc_method" and params.get("method") != "update_settings":
		frappe.throw(_("Meet document method is not allowed"), frappe.PermissionError)

	client = MeetBackendClient(get_backend_settings())
	try:
		return client.call(method_name, params)
	except MeetBackendError as exc:
		frappe.log_error(str(exc), "Meet Integration")
		frappe.throw(_(str(exc)), frappe.ValidationError)


def health():
	settings = get_backend_settings()
	request(
		"frappe.client.get_list",
		{"doctype": "Sae Meeting", "fields": ["name"], "limit_page_length": 1},
	)
	return {"connected": True, "server_url": settings["base_url"]}
