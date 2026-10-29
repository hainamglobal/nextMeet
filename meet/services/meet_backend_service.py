"""Application service for MTP's remote Meet operations."""

import frappe
from frappe import _

from meet.client.meet_backend_client import MeetBackendClient, MeetBackendError
from meet.config.backend import get_backend_settings, get_site_host_name


ALLOWED_METHODS = {
	"run_doc_method",
	"meet.api.meeting.create",
	"meet.api.meeting.get_sfu_connection_details",
	"meet.api.meeting.get_sfu_presence_preview_token",
	"meet.api.meeting.get_presence_counts",
	"meet.api.meeting.join_meeting",
	"meet.api.meeting.join_meeting_as_guest",
	"meet.api.meeting.get_waiting_room",
	"meet.api.meeting.approve_join_request",
	"meet.api.meeting.approve_all_join_requests",
	"meet.api.meeting.reject_join_request",
	"meet.api.meeting.promote_to_cohost",
	"meet.api.meeting.check_meeting_access",
	"meet.api.meeting.can_invite_meeting_users",
	"meet.api.meeting.invite_meeting_user",
	"meet.api.meeting.get_my_meeting_invitations",
	"meet.api.meeting.get_user_meetings",
	"meet.api.meeting.get_user_meeting",
	"meet.api.meeting.respond_meeting_invitation",
	"meet.api.integration.record_user_domain",
}


def request(method_name, params):
	if method_name not in ALLOWED_METHODS:
		frappe.throw(_("Meet method is not allowed"), frappe.PermissionError)

	if method_name == "run_doc_method":
		doctype = params.get("doctype") or params.get("dt")
		if doctype != "Sae Meeting":
			frappe.throw(_("Only Sae Meeting documents can be accessed"), frappe.PermissionError)
	if method_name == "run_doc_method" and params.get("method") != "update_settings":
		frappe.throw(_("Meet document method is not allowed"), frappe.PermissionError)

	params = dict(params)
	site_host_name = get_site_host_name()
	if method_name == "meet.api.meeting.create":
		params["host_name"] = site_host_name
	elif method_name == "meet.api.meeting.get_sfu_presence_preview_token":
		params["expected_host_name"] = site_host_name
	elif method_name == "meet.api.meeting.get_presence_counts":
		params["expected_host_name"] = site_host_name
	elif method_name == "meet.api.meeting.can_invite_meeting_users":
		params["expected_host_name"] = site_host_name
	elif method_name in {
		"meet.api.meeting.invite_meeting_user",
		"meet.api.meeting.get_my_meeting_invitations",
		"meet.api.meeting.get_user_meetings",
		"meet.api.meeting.get_user_meeting",
		"meet.api.meeting.respond_meeting_invitation",
	}:
		params["expected_host_name"] = site_host_name
	client = MeetBackendClient(get_backend_settings())
	try:
		result = client.call(method_name, params)
	except MeetBackendError as exc:
		frappe.log_error("Meet Integration", str(exc))
		exc_str = str(exc)
		if method_name == "meet.api.integration.record_user_domain" and (
			"404" in exc_str or "not found" in exc_str.lower() or "does not exist" in exc_str.lower()
		):
			frappe.throw(_("Mã cuộc họp không chính xác. Vui lòng kiểm tra lại."), frappe.ValidationError)
		frappe.throw(_(exc_str), frappe.ValidationError)

	return result


def health():
	settings = get_backend_settings()
	client = MeetBackendClient(settings)
	try:
		client.call(
			"frappe.client.get_list",
			{"doctype": "Sae Meeting", "fields": ["name"], "limit_page_length": 1},
		)
	except MeetBackendError as exc:
		frappe.log_error("Meet Integration", str(exc))
		frappe.throw(_(str(exc)), frappe.ValidationError)
	return {"connected": True, "server_url": settings["base_url"]}


def register_user_domain(meeting_id, user_email, user_name):
	site_host_name = get_site_host_name()
	return request(
		"meet.api.integration.record_user_domain",
		{
			"meeting_id": meeting_id,
			"user_email": user_email,
			"user_name": user_name,
			"host_name": site_host_name,
		},
	)


def configure_presence_callback(host_name, callback_url, callback_secret):
	site_host_name = get_site_host_name()
	if host_name.strip().lower().rstrip(".") != site_host_name:
		frappe.throw(_("Presence callback host does not match this site"), frappe.PermissionError)
	client = MeetBackendClient(get_backend_settings())
	try:
		return client.call(
			"meet.api.integration.configure_presence_callback",
			{
				"host_name": site_host_name,
				"callback_url": callback_url,
				"callback_secret": callback_secret,
			},
		)
	except MeetBackendError as exc:
		frappe.log_error("Meet Presence Registration", str(exc))
		frappe.throw(_("Could not register the MTP presence callback"), frappe.ValidationError)
