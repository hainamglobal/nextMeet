"""Persistent meeting chat history and message writes."""

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import now_datetime

from meet.utils.user import get_guest_session


def _get_chat_actor(meeting_id, guest_id=None):
	meeting = frappe.get_doc("Sae Meeting", meeting_id)
	if frappe.session.user == "Guest":
		guest_session = get_guest_session(guest_id) if guest_id else None
		if not guest_session or guest_session.get("meeting_id") != meeting_id:
			frappe.throw(_("Guest session is invalid or expired"), frappe.AuthenticationError)
		actor_id = guest_id
		actor_name = guest_session.get("guest_name") or actor_id
		is_guest = True
	else:
		actor_id = frappe.session.user
		actor_name, _ = frappe.db.get_value("User", actor_id, ["full_name", "email"]) or (actor_id, None)
		is_guest = False

	if meeting.is_user_banned(actor_id):
		frappe.throw(_("You are banned from this meeting"), frappe.PermissionError)
	if actor_id not in meeting.get_members() and not meeting.is_host_or_cohost(actor_id):
		frappe.throw(_("Join the meeting before accessing chat history"), frappe.PermissionError)

	return meeting, actor_id, actor_name, is_guest


def _serialize_message(message):
	return {
		"id": message.name,
		"user_id": message.sender_id,
		"user_name": message.sender_name,
		"message": message.message,
		"timestamp": str(message.sent_at),
		"client_id": message.client_id,
	}


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=120, seconds=60)
def get_history(meeting_id, guest_id=None, limit=200, start=0):
	if not meeting_id:
		frappe.throw(_("Meeting ID is required"), frappe.ValidationError)
	_get_chat_actor(meeting_id, guest_id)
	try:
		limit = min(max(int(limit), 1), 200)
		start = max(int(start), 0)
	except (TypeError, ValueError):
		frappe.throw(_("Invalid history pagination"), frappe.ValidationError)

	rows = frappe.get_all(
		"Sae Meeting Chat Message",
		filters={"meeting": meeting_id},
		fields=["name", "sender_id", "sender_name", "message", "sent_at", "client_id"],
		order_by="sent_at desc, creation desc",
		limit_start=start,
		limit_page_length=limit,
	)
	rows.reverse()
	return [
		{
			"id": row.name,
			"user_id": row.sender_id,
			"user_name": row.sender_name,
			"message": row.message,
			"timestamp": str(row.sent_at),
			"client_id": row.client_id,
		}
		for row in rows
	]


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=60, seconds=60)
def send_message(meeting_id, message, guest_id=None, client_id=None):
	if not meeting_id:
		frappe.throw(_("Meeting ID is required"), frappe.ValidationError)
	if not isinstance(message, str) or not message.strip():
		frappe.throw(_("Message cannot be empty"), frappe.ValidationError)
	message = message.strip()
	if len(message) > 2000:
		frappe.throw(_("Message cannot exceed 2000 characters"), frappe.ValidationError)

	meeting, actor_id, actor_name, is_guest = _get_chat_actor(meeting_id, guest_id)
	if meeting.host_only_chat and (is_guest or not meeting.is_host_or_cohost(actor_id)):
		frappe.throw(_("Only hosts and co-hosts can send messages right now"), frappe.PermissionError)

	if client_id is not None and not isinstance(client_id, str):
		frappe.throw(_("Client message ID is invalid"), frappe.ValidationError)
	client_id = (client_id or "").strip()[:100]
	if client_id:
		prior = frappe.db.get_value(
			"Sae Meeting Chat Message",
			{"meeting": meeting_id, "sender_id": actor_id, "client_id": client_id},
			"name",
		)
		if prior:
			return _serialize_message(frappe.get_doc("Sae Meeting Chat Message", prior))

	doc = frappe.get_doc(
		{
			"doctype": "Sae Meeting Chat Message",
			"meeting": meeting_id,
			"sender_id": actor_id,
			"sender_name": actor_name,
			"message": message,
			"client_id": client_id,
			"sent_at": now_datetime(),
		}
	).insert(ignore_permissions=True)
	return _serialize_message(doc)
